# a slightly modified ocr.py from pysjtu (onnx version)
from io import BytesIO

import numpy as np
import onnxruntime as rt

from utils import *


class Recognizer:
    """ Base class for Recognizers """
    pass


class LegacyRecognizer(Recognizer):
    """
    An SVM-based captcha recognizer.

    It first applies projection-based algorithm to the input image, then use a pre-trained SVM model
    to predict the answer.

    It's memory and cpu efficient. The accuracy is around 90%.
    """

    def __init__(self, model_file: str = "svm_model.onnx"):
        self._clr = rt.InferenceSession(model_file)
        self._table = [0] * 156 + [1] * 100

    def recognize(self, img: bytes):
        """
        Predict the captcha.

        :param img: An PIL Image containing the captcha.
        :return: captcha in plain text.
        """
        img_rec = Image.open(BytesIO(img))
        img_rec = img_rec.convert("L")
        img_rec = img_rec.point(self._table, "1")

        segments = [normalize(v_split(segment)).convert("L").getdata() for segment in h_split(img_rec)]

        np_segments = [np.array(segment, dtype=np.float32) for segment in segments]
        predicts = [self._clr.run(None, {self._clr.get_inputs()[0].name: np_segment}) for np_segment in np_segments]
        return "".join([str(predict[0][0]) for predict in predicts])


class NNRecognizer(Recognizer):
    """
    A ResNet-20 based captcha recognizer.

    It feeds the image directly into a pre-trained ResNet-20 model to predict the answer.

    It consumes more memory and computing power than :class:`SVMRecognizer`. The accuracy is around 98%.

    This recognizer requires pytorch and torchvision to work.

    .. note::

        You may set the flag `use_cuda` to speed up predicting, but be aware that it takes time to load the model
        into your GPU and there won't be significant speed-up unless you have a weak CPU.
    """

    def __init__(self, model_file: str = "nn_model.onnx"):
        self._table = [0] * 156 + [1] * 100
        self._sess = rt.InferenceSession(model_file)

    @staticmethod
    def _tensor_to_captcha(tensors):
        captcha = ""
        for tensor in tensors:
            asc = int(np.argmax(tensor, 1))
            if asc < 26:
                captcha += chr(ord("a") + asc)
        return captcha

    def recognize(self, img: bytes):
        """
        Predict the captcha.

        :param img: An PIL Image containing the captcha.
        :return: captcha in plain text.
        """
        img_rec = Image.open(BytesIO(img))
        img_rec = img_rec.convert("L")
        img_rec = img_rec.point(self._table, "1")
        img_np = np.array(img_rec, dtype=np.float32)
        img_np = np.expand_dims(img_np, 0)
        img_np = np.expand_dims(img_np, 0)

        out_tensor = self._sess.run(None, {self._sess.get_inputs()[0].name: img_np})
        output = NNRecognizer._tensor_to_captcha(out_tensor)
        return output
