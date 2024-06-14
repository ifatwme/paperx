import cv2
import numpy as np
from matplotlib import pyplot as plt


class ImageProcessor:
    def __init__(self, image_path):
        self._image_path = image_path
        self.load_image()
        self._image = self._base_image.copy()

    def load_image(self, image_path=None):
        if image_path is None:
            image_path = self._image_path
        self._base_image = cv2.imread(image_path)

    def reset_image(self):
        self._image = self._base_image

    def save_image(self, image_path=None, image=None):
        image = self.check_image(image)
        if image_path is None:
            image_path = self._image_path
        cv2.imwrite(image_path, image)

    def check_inplace(self, image, inplace: bool):
        if inplace:
            self._image = image

    def check_image(self, image):
        if image is None:
            return self._image
        return image

    def display_image(self, image=None):
        image = self.check_image(image)
        fig = plt.figure(
            figsize=(
                image.shape[1] / float(200),
                image.shape[0] / float(200),
            )
        )
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.imshow(image, cmap="gray")
        plt.show()

    def get_inverted(self, in_image: bool = None, inplace: bool = False):
        in_image = self.check_image(in_image)
        out_image = cv2.bitwise_not(in_image)
        self.check_inplace(out_image, inplace)
        return out_image

    def get_gray_scale(self, in_image: bool = None, inplace: bool = False):
        in_image = self.check_image(in_image)
        out_image = cv2.cvtColor(in_image, cv2.COLOR_BGR2GRAY)
        self.check_inplace(in_image, inplace)
        return out_image

    def get_blur(self, ksize: tuple, in_image: bool = None, inplace: bool = False):
        in_image = self.check_image(in_image)
        out_image = cv2.GaussianBlur(in_image, ksize, 0)
        self.check_inplace(out_image, inplace)
        return out_image

    def get_threshold(
        self, params: tuple = (100, 252), in_image: bool = None, inplace: bool = False
    ):
        in_image = self.check_image(in_image)
        out_image = cv2.threshold(
            in_image, params[0], params[1], cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )[1]
        self.check_inplace(out_image, inplace)
        return out_image

    def get_remove_noise(
        self,
        kernel_dilate: tuple = (1, 1),
        kernel_erode: tuple = (1, 1),
        iteration_dilate: int = 1,
        iteration_erode: int = 1,
        ksize: int = 3,
        in_image: bool = None,
        inplace: bool = False,
    ):
        in_image = self.check_image(in_image)
        out_image = cv2.medianBlur(
            cv2.erode(
                cv2.dilate(
                    in_image,
                    np.ones(kernel_dilate, np.uint8),
                    iterations=iteration_dilate,
                ),
                np.ones(kernel_erode, np.uint8),
                iterations=iteration_erode,
            ),
            ksize,
        )
        self.check_inplace(out_image, inplace)
        return out_image

    def get_thin_font(
        self,
        kernel: tuple = (2, 2),
        iteration: int = 1,
        in_image: bool = None,
        inplace: bool = False,
    ):
        in_image = self.check_image(in_image)
        out_image = cv2.bitwise_not(
            cv2.erode(
                cv2.bitwise_not(in_image),
                np.ones(kernel, np.uint8),
                iterations=iteration,
            )
        )
        self.check_inplace(out_image, inplace)
        return out_image

    def get_thick_font(
        self,
        kernel: tuple = (2, 2),
        iteration: int = 1,
        in_image=None,
        inplace: bool = False,
    ):
        in_image = self.check_image(in_image)
        out_image = cv2.bitwise_not(
            cv2.dilate(
                cv2.bitwise_not(in_image),
                np.ones(kernel, np.uint8),
                iterations=iteration,
            )
        )
        self.check_inplace(out_image, inplace)
        return out_image

    def preprocess(
        self,
        params: tuple = (252, 252),
        kernel_dilate: tuple = (1, 1),
        kernel_erode: tuple = (1, 1),
        iteration_dilate: int = 1,
        iteration_erode: int = 1,
        ksize: int = 3,
    ):
        self.get_gray_scale()
        self.get_threshold(params)
        self.get_remove_noise(
            kernel_dilate, kernel_erode, iteration_dilate, iteration_erode, ksize
        )

    def get_dilate(
        self,
        dilation_shape: tuple,
        iterations: int = 1,
        in_image=None,
        inplace: bool = False,
    ):
        in_image = self.check_image(in_image)
        element = cv2.getStructuringElement(cv2.MORPH_RECT, dilation_shape)
        out_image = cv2.dilate(in_image, element, iterations=iterations)
        self.check_inplace(out_image, inplace)
        return out_image

    def get_segment(
        self,
        dilate,
        h_thresh: int = 0,
        w_thresh: int = 0,
        roi_avg: bool = False,
        in_image=None,
        inplace: bool = False,
    ):
        # area = self.get_dilate(kernel, iterations)
        in_image = self.check_image(in_image)
        out_image = in_image.copy()
        contours = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if len(contours) == 2 else contours[1]
        contours = sorted(
            contours, key=lambda x: cv2.boundingRect(x)[1] + cv2.boundingRect(x)[0]
        )
        # cv2.drawContours(image, contours, -1, (255,0,0), 2)
        roi = []
        if roi_avg:
            h_thresh = np.sum(
                cv2.boundingRect(contour)[3] for contour in contours
            ) / len(contours)
            w_thresh = np.sum(
                cv2.boundingRect(contour)[2] for contour in contours
            ) / len(contours)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if h > h_thresh and w > w_thresh:
                roi.append((in_image[y : y + h, x : x + w], [x, y, w, h]))
                cv2.rectangle(out_image, (x, y), (x + w, y + h), (36, 255, 12), 2)
        self.check_inplace(out_image, inplace)
        return out_image, roi


if __name__ == "__main__":
    pass
