import cv2
import sys
import numpy as np

def stackFast(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        sys.exit("Error: Could not open video file.")
    stack = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if stack is None:
            stack = frame 
        else: 
            stack = np.maximum(stack, frame)
    cap.release()
    return stack

if __name__ == "__main__":
    video_file = sys.argv[1]
    stack_file = video_file.replace(".mp4", "-stack.jpg")
    stack = stackFast(video_file)
    cv2.imshow('stack', stack)
    cv2.waitKey(0)
    cv2.destroyAllWindows
    cv2.imwrite(stack_file, stack) 