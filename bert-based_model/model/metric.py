import torch
import numpy as np


def accuracy(predict, target):
    with torch.no_grad():
        correct = 0
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        predict, target = predict.type(torch.LongTensor).to(device), target.type(torch.LongTensor).to(device)
        for p_r, t_r in zip(predict, target):
            if torch.equal(t_r, p_r):
                correct += 1
        ret = correct / len(target)
    return ret

def microF1(predict, target):
    num_classes = 6
    with torch.no_grad():
        total_len = len(predict)
        tp = np.zeros(num_classes) 
        fp = np.zeros(num_classes) 
        fn = np.zeros(num_classes) 
        for i in range(total_len):
            for j in range(num_classes):
                if target[i][j].item() == 1 and predict[i][j].item() == 1:
                    tp[j] += 1
                elif target[i][j].item() == 1 and predict[i][j].item() == 0:
                    fn[j] += 1
                elif target[i][j].item() == 0 and predict[i][j].item() == 1:
                    fp[j] += 1
        #print(tp,fp,fn)
        tp_total = np.sum(tp)
        fp_total = np.sum(fp)
        fn_total = np.sum(fn)

        epison = 1E-6
        p = tp_total / (tp_total + fp_total + epison)
        r = tp_total / (tp_total + fn_total + epison)
    return (2 * p * r) / ( p + r + epison)

def tp(predict, target):
    num_classes = 6
    with torch.no_grad():
        total_len = len(predict)
        tp = np.zeros(num_classes) 
        for i in range(total_len):
            for j in range(num_classes):
                if target[i][j].item() == 1 and predict[i][j].item() == 1:
                    tp[j] += 1
        tp_total = np.sum(tp)
    return tp_total

def fp(predict, target):
    num_classes = 6
    with torch.no_grad():
        fp = np.zeros(num_classes) 
        total_len = len(predict)
        for i in range(total_len):
            for j in range(num_classes):
                if target[i][j].item() == 0 and predict[i][j].item() == 1:
                    fp[j] += 1
        fp_total = np.sum(fp)
    return fp_total

def fn(predict, target):
    num_classes = 6
    with torch.no_grad():
        total_len = len(predict)
        fn = np.zeros(num_classes) 
        for i in range(total_len):
            for j in range(num_classes):
                if target[i][j].item() == 1 and predict[i][j].item() == 0:
                    fn[j] += 1
        fn_total = np.sum(fn)
    return fn_total



def top_k_acc(output, target, k=3):
    with torch.no_grad():
        pred = torch.topk(output, k, dim=1)[1]
        assert pred.shape[0] == len(target)
        correct = 0
        for i in range(k):
            correct += torch.sum(pred[:, i] == target).item()
    return correct / len(target)
