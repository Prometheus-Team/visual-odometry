#!/usr/bin/env python
# coding: utf-8

__author__ = "Masahiko Toyoshi"
__copyright__ = "Copyright 2007, Masahiko Toyoshi."
__license__ = "GPL"
__version__ = "1.0.0"

import argparse
import cv2
import numpy as np
import matplotlib.pyplot as plt
from dataset import create_dataset
import math
import video
import time


def parse_argument():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='kitti')
    parser.add_argument('--path', required=True)

    return parser.parse_args()


def calc_euclid_dist(p1, p2):
    a = math.pow((p1[0] - p2[0]), 2.0) + math.pow((p1[1] - p2[1]), 2.0)
    return math.sqrt(a)


def takeResponseValue(element):
    return element.response


def main():
    options = parse_argument()
    dataset = create_dataset(options)

    # get input from video
    inputStream = video.create_capture(options.path)

    feature_detector = cv2.FastFeatureDetector_create(threshold=25,
                                                      nonmaxSuppression=True)

    lk_params = dict(winSize=(21, 21),
                     criteria=(cv2.TERM_CRITERIA_EPS |
                               cv2.TERM_CRITERIA_COUNT, 30, 0.03))

    current_pos = np.zeros((3, 1))
    current_rot = np.eye(3)

    # create graph.
    position_figure = plt.figure()
    position_axes = position_figure.add_subplot(1, 1, 1)
    error_figure = plt.figure()
    rotation_error_axes = error_figure.add_subplot(1, 1, 1)
    rotation_error_list = []
    frame_index_list = []

    position_axes.set_aspect('equal', adjustable='box')

    print("{} images found.".format(dataset.image_count))

    prev_image = None

    # ? Ground truth from KITTI
    valid_ground_truth = False
    if dataset.ground_truth is not None:
        valid_ground_truth = True

    # If Camera matrix is provided or use default
    if dataset.camera_matrix is not None:
        camera_matrix = dataset.camera_matrix()
    else:
        camera_matrix = np.array([[718.8560, 0.0, 607.1928],
                                  [0.0, 718.8560, 185.2157],
                                  [0.0, 0.0, 1.0]])
    

    trackedPoints = []

    while True:
        # load image

        # ? Read image file
        # image = cv2.imread(dataset.image_path_left(index))

        # Read a frame from a video file
        _ret, image = inputStream.read()

        if (_ret == False):
            break

        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # main process
        keypoint = feature_detector.detect(image, None)

        # Take 1000 best key points
        keypoint.sort(key=takeResponseValue, reverse=True)
        keypoint = keypoint[0:1000]

        if len(keypoint) < 10:
            # print("Keypoints/Features are under threshold: ", keypoint)
            continue

        if prev_image is None:
            prev_image = image
            prev_keypoint = keypoint
            continue


        # points = np.array(list(map(lambda x: [x.pt], prev_keypoint)),
        #                   dtype=np.float32)


        # !Start Time
        startTime = time.time()

        points = np.array([[x.pt] for x in prev_keypoint], dtype=np.float32)
        
        p1, st, err = cv2.calcOpticalFlowPyrLK(prev_image,
                                               image, points,
                                               None, **lk_params)

        E, mask = cv2.findEssentialMat(p1, points, camera_matrix,
                                       cv2.RANSAC, 0.999, 1.0, None)

        points, R, t, mask = cv2.recoverPose(E, p1, points, camera_matrix)

        scale = 1.0

        # TODO: *here. calc scale from ground truth if exists.

        current_pos += current_rot.dot(t) * scale
        current_rot = R.dot(current_rot)

        # TODO: *here. get ground truth if exists.

        # TODO: *here. calc rotation error with ground truth.

        trackedPoints.append(current_pos.copy())
        position_axes.scatter(current_pos[0][0], current_pos[2][0])
        
        # ? Uncomment the next line to see realtime output graph
        # plt.pause(.01)

        img = cv2.drawKeypoints(image, keypoint, None)

        # ? Uncomment the next line to see the video feed
        # cv2.imshow('feature', img)
        # cv2.imshow('image', image)

        cv2.waitKey(1)
        
        prev_image = image
        prev_keypoint = keypoint

        # !Stop Time
        duration = time.time() - startTime
        print("Duration: ",duration)

    
    with open("output_data" + str(time.time()) + ".csv", "w") as out_file:
        for i in range(len(trackedPoints)):
            out_string = ""
            out_string += str(trackedPoints[i][0]) 
            # out_string += ", " + str(trackedPoints[i][1]) 
            out_string += ", " + str(trackedPoints[i][2]) + "\n"
            out_file.write(out_string)

    position_figure.savefig("position_plot.png")
    rotation_error_axes.bar(frame_index_list, rotation_error_list)
    error_figure.savefig("error.png")

if __name__ == "__main__":
    main()
