import os
import cv2
import struct
import shutil
import copy
import glob
import argparse
import trimesh
import numpy as np
import open3d as o3d
from tqdm import tqdm
from PIL import Image
import imageio
import sys
sys.path.append('/workspace/gim_3d/')
from utils.colmap_utils import Colmap
from utils.depth_utils import *

def resize_depth(depth, rgb):
    new_depth = np.array(
        Image.fromarray(depth, mode="F").resize(
            (rgb.shape[1], rgb.shape[0]), resample=Image.Resampling.NEAREST
        )
    )
    return new_depth

def resize(rgb, depth, intrinsic, scale):
    if scale != 1:
        new_depth = np.array(
                Image.fromarray(depth, mode="F").resize(
                    (int(depth.shape[1]*scale), int(depth.shape[0]*scale)), resample=Image.Resampling.NEAREST
                )
            )
        new_rgb = np.array(
                Image.fromarray(rgb).resize(
                    (int(rgb.shape[1]*scale), int(rgb.shape[0]*scale)), resample=Image.Resampling.BICUBIC
                )
            )
        new_intrinsic = intrinsic.copy()
        new_intrinsic = new_intrinsic[:2]*scale
        return new_rgb, new_depth, new_intrinsic
    else:
        return rgb, depth, intrinsic



def convert_to_apple_stream(scene_id, data_dir, mesh_f, out_dir):

    os.makedirs(out_dir, exist_ok=True)

    print("start reading mesh ...")

    mesh = o3d.io.read_triangle_mesh(mesh_f)
    vert = np.array(mesh.vertices)
    face_id = np.array(mesh.triangles)
    # tex_vs = np.array(mesh.triangle_uvs)
    print("\nmesh: ", vert.shape, face_id.shape, "\n")
    print("... done.")

    # for i in tqdm(range(face_id.shape[0])):
    #     assert (
    #         (face_id[i, 0] != face_id[i, 1])
    #         and (face_id[i, 0] != face_id[i, 2])
    #         and (face_id[i, 1] != face_id[i, 2])
    #     ), f"{face_id[i, :]}"

    with open(os.path.join(out_dir, "Vertices.0"), "wb") as f:
        f.write(vert.astype(np.float32).tobytes())
    with open(os.path.join(out_dir, "Faces.0"), "wb") as f:
        f.write(face_id.astype(np.uint32).tobytes())

    print("start reading rgb-d ...")

    depth_image_path = os.path.join(data_dir, "depth_packed")
    color_image_path = os.path.join(data_dir, "images")

    print("... done.")

    # NOTE: since we will resize depth to the same resolution as RGB,
    # we direclty use RGB's intrinsics.
    # K = np.loadtxt(os.path.join(data_dir, "intrinsic/intrinsic_color.txt"))

    print("start writing stream file ...")
    cnt = 0
    newFile = open(os.path.join(out_dir, "Recv.stream"), "wb")

    # NOTE: we need to keep the order of image indices
    colmap = Colmap()
    images_txt = colmap.read_images_text(os.path.join(data_dir,'images.txt'))
    cameras_txt = colmap.read_cameras_text(os.path.join(data_dir,'cameras.txt'))
    intrinsics = colmap.get_intrinsics(cameras_txt)
    extrinsics = colmap.read_keylog(os.path.join(data_dir,'key.log'))
    count = 0
    for img_id, img in tqdm(dict(sorted(images_txt.items())).items()):
        # count+=1
        # if count > 3:
        #     break
        img_name = images_txt[img_id].name[:-4]+'.JPG'
        depth_name = images_txt[img_id].name[:-4]+'.png'
        depth = unpack_float32(np.asarray((imageio.v2.imread(os.path.join(depth_image_path, depth_name)))))
        depth[np.isnan(depth)] = 0
        depth[np.isinf(depth)] = 0
        # depth = depth / 1000.
        image = imageio.v2.imread(os.path.join(color_image_path, img_name))

        viewMatrix = np.linalg.inv(extrinsics[img_id])
        K = intrinsics[img.camera_id]

        resized_image, resized_depth, K = resize(image, depth, K, 0.4)
        # image[mask == 0] = 255

        # when writing to file, we transpose data to mimic Apple's Fortran order
        cnt = cnt + 1
        newFile.write(struct.pack("3I", *resized_image.shape))
        newFile.write(resized_image.transpose((2, 1, 0)).astype(np.uint8).tobytes())
        newFile.write(struct.pack("2I", *resized_depth.shape))
        newFile.write(resized_depth.transpose((1, 0)).astype(np.float32).tobytes())

        # NOTE: start processing camera poses
        # This is camera-to-world: https://github.com/ScanNet/ScanNet/tree/488e5ba/SensReader/python
        
        # cam2world_mat = np.loadtxt(os.path.join(data_dir, f"pose/{i:06d}.txt"))
        
        # NOTE: start processing projection matrix
        # originally, projection matrix maps to NDC with range [0, 1]
        # to align with our CPP implementation, we modify it to make points mapped to NDC with range [-1, 1].
        # Specifically, assume original projection matrix is the following:
        # M1 = [[fu, 0, u],
        #       [0, fv, v],
        #       [0, 0,  1]]
        # where fu, fv are focal lengths and (u, v) marks the principal point.
        # Now we change the projection matrix to:
        # M2 = [[2fu, 0,   2u - 1],
        #       [0,   2fv, 2v - 1],
        #       [0,   0,   1]]
        #
        # The validity can be verified as following:
        # a) left end value:
        # assume point p0 = (h0, w0, 1)^T is mapped to (0, 0, 1), namely:
        # M1 * p0 = (0, 0, 1)^T
        # ==> h0 = -u / fu, w0 = -v / fv
        # ==> M2 * p0 = (-1, -1, 1)
        #
        # b) right end value:
        # assume point p1 = (h1, w1, 1)^T is mapped to (1, 1, 1), namely:
        # M1 * p1 = (1, 1, 1)^T
        # ==> h1 = (1 - u) / fu, w0 = (1 - v) / fv
        # ==> M2 * p1 = (1, 1, 1)
        img_h, img_w, _ = resized_image.shape
        prjMatrix = np.eye(4)
        prjMatrix[0, 0] = 2 * K[0, 0] / img_w
        prjMatrix[1, 1] = 2 * K[1, 1] / img_h
        prjMatrix[0, 2] = 2 * K[0, 2] / img_w - 1
        prjMatrix[1, 2] = 2 * K[1, 2] / img_h - 1
        prjMatrix[2, 2] = 1
        prjMatrix[3, 3] = 0
        prjMatrix[3, 2] = 1

        # make 1st elem for height, 2nd elem for width
        prjMatrix = prjMatrix[(1, 0, 2, 3), :]

        # NOTE: we need to flip left-right to align with Apple format's convention
        prjMatrix[1, :] = -prjMatrix[1, :]

        # to align with Apple's Fortran order
        newFile.write(viewMatrix.transpose((1, 0)).astype(np.float32).tobytes())
        newFile.write(prjMatrix.transpose((1, 0)).astype(np.float32).tobytes())

    newFile.close()

    print("... done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str)
    parser.add_argument("--mesh_f", type=str)
    parser.add_argument("--scene_id", type=str)
    parser.add_argument(
        "--out_dir",
        type=str,
        required=True,
        help="Directory for saving processed data",
    )
    args = parser.parse_args()

    # out_dir = os.path.join(args.input_dense_dir, "apple_format")

    print(f"\ndata_dir: {args.data_dir}\n")
    print(f"\nout_dir: {args.out_dir}\n")

    convert_to_apple_stream(args.scene_id, args.data_dir, args.mesh_f, args.out_dir)
