import numpy as np
import onnxruntime
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError
from tokenizers import Tokenizer

from game_rag import config


def model_file(model, name):
    # use the copy on disk, only go online the first time
    try:
        return hf_hub_download(model, name, local_files_only=True)
    except LocalEntryNotFoundError:
        return hf_hub_download(model, name)


class Reranker:
    def __init__(self, model=config.RERANK_MODEL):
        self.tokenizer = Tokenizer.from_file(model_file(model, "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=512)
        self.model = onnxruntime.InferenceSession(
            model_file(model, "onnx/model.onnx"), providers=["CPUExecutionProvider"],
        )
        self.input_names = {i.name for i in self.model.get_inputs()}

    def score(self, question, text):
        # question and chunk go in together as one input, that's what makes it a cross-encoder
        pair = self.tokenizer.encode(question, text)
        inputs = {"input_ids": pair.ids, "attention_mask": pair.attention_mask, "token_type_ids": pair.type_ids}
        feed = {name: np.array([v], dtype=np.int64) for name, v in inputs.items() if name in self.input_names}
        return float(self.model.run(None, feed)[0][0][0])

    def scores(self, question, texts):
        return [self.score(question, t) for t in texts]
