"""Export a quantized Transformers.js encoder from the published research retriever."""

import gc
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModel,AutoTokenizer

from review_cv import ENCODERS


class TokenEncoder(torch.nn.Module):
    def __init__(self,model):
        super().__init__()
        self.model=model

    def forward(self,input_ids,attention_mask,token_type_ids):
        return self.model(input_ids=input_ids,attention_mask=attention_mask,
                          token_type_ids=token_type_ids).last_hidden_state


def main():
    repo,revision=ENCODERS["fine-tuned"]
    model=TokenEncoder(AutoModel.from_pretrained(repo,revision=revision,attn_implementation="eager")).eval()
    tokenizer=AutoTokenizer.from_pretrained(repo,revision=revision)
    tokens=tokenizer(["Debug a slow database query.","Sorgu planını inceledim."],padding=True,return_tensors="pt")
    names=["input_ids","attention_mask","token_type_ids"]
    output=Path(__file__).resolve().parents[1]/"runs/browser-retriever/onnx"
    output.mkdir(parents=True,exist_ok=True)
    floating=output/"model.onnx"
    torch.onnx.export(model,tuple(tokens[name] for name in names),str(floating),
                      input_names=names,output_names=["last_hidden_state"],opset_version=17,dynamo=False,
                      dynamic_axes={name:{0:"batch",1:"sequence"} for name in names+["last_hidden_state"]})
    del model
    gc.collect()
    quantize_dynamic(str(floating),str(output/"model_quantized.onnx"),weight_type=QuantType.QUInt8,
                     op_types_to_quantize=["MatMul","Gather"])
    print((output/"model_quantized.onnx").stat().st_size,"bytes")


if __name__=="__main__":
    main()
