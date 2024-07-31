import cv2
import threading
from PIL import Image, ImageTk
import tkinter as tk


class VideoStreamHandler:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.cap = cv2.VideoCapture(0)
        self.photo = None
        self.current_frame = None
        self.thread_running = False

    def video_stream(self):
        while self.thread_running:
            if not self.cap.isOpened():
                self.cap.open(0)
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                self.photo = ImageTk.PhotoImage(image=img)
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                self.root.update()

    def start_stream(self):
        self.thread_running = True
        self.thread = threading.Thread(target=self.video_stream)
        self.thread.start()

    def stop_video(self):
        self.thread_running = False
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

    def get_current_frame(self):
        return self.current_frame
