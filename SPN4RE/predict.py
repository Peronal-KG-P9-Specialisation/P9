import argparse, os, torch
import random
import numpy as np
from models.setpred4RE import SetPred4RE
from utils.data import build_data
from main import str2bool,add_argument_group, get_args,set_seed
try:
    from transformers import BertTokenizer
except:
    from pytorch_transformers import BertTokenizer




def remove_accents(text: str) -> str:
    accents_translation_table = str.maketrans(
    "áéíóúýàèìòùỳâêîôûŷäëïöüÿñÁÉÍÓÚÝÀÈÌÒÙỲÂÊÎÔÛŶÄËÏÖÜŸ",
    "aeiouyaeiouyaeiouyaeiouynAEIOUYAEIOUYAEIOUYAEIOUY"
    )
    return text.translate(accents_translation_table)

parser = argparse.ArgumentParser()

def from_main():
    data_arg = add_argument_group('Data')
    """python3 -m main --max_epoch 10 --use_gpu False"""
    data_arg.add_argument('--dataset_name', type=str, default="WebNLG")
    data_arg.add_argument('--train_file', type=str, default="./data/WebNLG/clean_WebNLG/train_new_new_v2.json")
    data_arg.add_argument('--valid_file', type=str, default="./data/WebNLG/clean_WebNLG/valid_new_new_v2.json")
    data_arg.add_argument('--test_file', type=str, default="./data/WebNLG/clean_WebNLG/test_new_new_v2.json")

    data_arg.add_argument('--generated_data_directory', type=str, default="./data/generated_data/")
    data_arg.add_argument('--generated_param_directory', type=str, default="./data/generated_data/model_param/")
    data_arg.add_argument('--bert_directory', type=str, default="/home/test/Github/bert/bert-base-cased")
    data_arg.add_argument("--partial", type=str2bool, default=False)
    learn_arg = add_argument_group('Learning')
    learn_arg.add_argument('--model_name', type=str, default="Set-Prediction-Networks")
    learn_arg.add_argument('--num_generated_triples', type=int, default=10)
    learn_arg.add_argument('--num_decoder_layers', type=int, default=4)
    learn_arg.add_argument('--matcher', type=str, default="avg", choices=['avg', 'min'])
    learn_arg.add_argument('--na_rel_coef', type=float, default=0.25)
    learn_arg.add_argument('--rel_loss_weight', type=float, default=1)
    learn_arg.add_argument('--head_ent_loss_weight', type=float, default=2)
    learn_arg.add_argument('--tail_ent_loss_weight', type=float, default=2)
    learn_arg.add_argument('--fix_bert_embeddings', type=str2bool, default=True)
    learn_arg.add_argument('--batch_size', type=int, default=8)
    learn_arg.add_argument('--max_epoch', type=int, default=50)
    learn_arg.add_argument('--gradient_accumulation_steps', type=int, default=1)
    learn_arg.add_argument('--decoder_lr', type=float, default=0.00005)
    learn_arg.add_argument('--encoder_lr', type=float, default=0.00002)
    learn_arg.add_argument('--lr_decay', type=float, default=0.02)
    learn_arg.add_argument('--weight_decay', type=float, default=0.000001)
    learn_arg.add_argument('--max_grad_norm', type=float, default=20)
    learn_arg.add_argument('--optimizer', type=str, default='AdamW', choices=['Adam', 'AdamW'])
    evaluation_arg = add_argument_group('Evaluation')
    evaluation_arg.add_argument('--n_best_size', type=int, default=100)
    evaluation_arg.add_argument('--max_span_length', type=int, default=10)
    misc_arg = add_argument_group('MISC')
    misc_arg.add_argument('--refresh', type=str2bool, default=False)
    misc_arg.add_argument('--use_gpu', type=str2bool, default=True)
    misc_arg.add_argument('--visible_gpu', type=int, default=1)
    misc_arg.add_argument('--random_seed', type=int, default=1)

    args, unparsed = get_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.visible_gpu)
    for arg in vars(args):
            print(arg, ":",  getattr(args, arg))
    set_seed(args.random_seed)
    return args
args = from_main()

def predict_triples(utterance, model, tokenizer, relation_alphabet):
    token_sent = [tokenizer.cls_token] + tokenizer.tokenize(remove_accents(utterance)) + [tokenizer.sep_token]
    sent_ids = tokenizer.convert_tokens_to_ids(token_sent)
    max_sent_len = len(sent_ids)
    input_ids = torch.zeros((1, max_sent_len), requires_grad=False).long()
    attention_mask = torch.zeros((1, max_sent_len), requires_grad=False, dtype=torch.float32)
    input_ids[0, :max_sent_len] = torch.LongTensor(sent_ids)
    attention_mask[0, :max_sent_len] = torch.FloatTensor([1] * max_sent_len)
    info ={"seq_len":[max_sent_len],"sent_idx":[0]}
    output = model.gen_triples(input_ids, attention_mask, info)
    triples = list()
    for i in range(len(output[0])):
        relation = output[0][i].pred_rel
        relation = relation_alphabet.get_instance(relation)
        head_s = output[0][i].head_start_index
        head_e = output[0][i].head_end_index
        tail_s = output[0][i].tail_start_index
        tail_e = output[0][i].tail_end_index
        head = token_sent[head_s:head_e+1]
        head = " ".join([x for x in head]).replace(" ##","")
        tail = token_sent[tail_s:tail_e+1]
        tail = " ".join([x for x in tail]).replace(" ##","")
        triples.append((head,relation,tail))
    return triples

def load_model(path_model, args):
    model = SetPred4RE(args, 61)
    state_dict = torch.load(path_model)
    model.load_state_dict(state_dict["state_dict"])
    return model

tokenizer = BertTokenizer.from_pretrained("BERT DIR", do_lower_case=False)
data = build_data(args)
model = load_model("/home/test/Github/code/SPN4RE/data/generated_data/model_param/SetPred4RE_WebNLG_epoch_0_f1_0.3946.model",args)
#SetPred4RE(args, data.relational_alphabet.size())
#test
utterance = "my mom had me in mcdonalds ."
triples = predict_triples(utterance,model,tokenizer,data.relational_alphabet)