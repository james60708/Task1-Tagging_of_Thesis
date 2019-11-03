from tqdm import tqdm
import numpy as np
import torch
import torch.nn as nn
from torchvision.utils import make_grid
from base import BaseTrainer
from utils import inf_loop, MetricTracker


class Trainer(BaseTrainer):
    """
    Trainer class
    """
    def __init__(self, model, criterion, metric_ftns, optimizer, config, data_loader,
                 valid_data_loader=None, lr_scheduler=None, len_epoch=None):
        super().__init__(model, criterion, metric_ftns, optimizer, config)
        self.config = config
        self.data_loader = data_loader

        
        if len_epoch is None:
            # epoch-based training
            self.len_epoch = len(self.data_loader)
        else:
            # iteration-based training
            self.data_loader = inf_loop(data_loader)
            self.len_epoch = len_epoch
        self.valid_data_loader = valid_data_loader
        self.do_validation = self.valid_data_loader is not None
        self.lr_scheduler = lr_scheduler
        self.log_step = int(self.len_epoch / 4) # int(np.sqrt(data_loader.batch_size))

        self.train_metrics = MetricTracker('loss', *[m.__name__ for m in self.metric_ftns], writer=self.writer)
        self.valid_metrics = MetricTracker('loss', *[m.__name__ for m in self.metric_ftns], writer=self.writer)

    def _train_epoch(self, epoch):
        """
        Training logic for an epoch

        :param epoch: Integer, current training epoch.
        :return: A log that contains average loss and metric in this epoch.
        """
        self.model.train()
        self.train_metrics.reset()
        trange = tqdm(enumerate(self.data_loader), total=self.len_epoch, desc="training")
        for batch_idx, batch in trange:
            data = batch["sentence"]
            target = batch["label"]

            if not isinstance(data, list):   # check if type is list
                data, target = data.to(self.device), target.to(self.device)

            self.optimizer.zero_grad()
            output = self.model(data)

            if isinstance(output, list):   
                output = torch.cat(output, dim=0).to(self.device)
                target = torch.cat(target, dim=0).to(self.device)

            loss = self.criterion(output, target)
            loss.backward()
            self.optimizer.step()

            self.writer.set_step((epoch - 1) * self.len_epoch + batch_idx)
            self.train_metrics.update('loss', loss.item())

            predict = (output >= 0.5)
            maxclass = torch.argmax(output, dim=1) # make sure every sentence predicted to at least one class
            for i in range(len(predict)):
                predict[i][maxclass[i].item()] = 1
            predict = predict.type(torch.LongTensor).to(self.device)

            for met in self.metric_ftns:
                self.train_metrics.update(met.__name__, met(predict, target))

            '''
            if batch_idx % self.log_step == 0:
                self.logger.debug('Train Epoch: {} {} Loss: {:.6f}'.format(
                    epoch,
                    self._progress(batch_idx),
                    loss.item()))
                self.writer.add_image('input', make_grid(data.cpu(), nrow=8, normalize=True))
            '''
            if batch_idx == self.len_epoch:
                break
            trange.set_postfix(loss=loss.item())
        log = self.train_metrics.result()

        if self.do_validation:
            val_log = self._valid_epoch(epoch)
            log.update(**{'val_'+k : v for k, v in val_log.items()})

        if self.lr_scheduler is not None:
            self.lr_scheduler.step()
        return log

    def _valid_epoch(self, epoch):
        """
        Validate after training an epoch

        :param epoch: Integer, current training epoch.
        :return: A log that contains information about validation
        """
        self.model.eval()
        self.valid_metrics.reset()
        with torch.no_grad():
            for batch_idx, batch in enumerate(self.valid_data_loader):
                data = batch["sentence"]
                target = batch["label"]

                if not isinstance(data, list):   
                    data, target = data.to(self.device), target.to(self.device)

                output = self.model(data)

                if isinstance(output, list):   
                    output = torch.cat(output, dim=0).to(self.device)
                    target = torch.cat(target, dim=0).to(self.device)

                loss = self.criterion(output, target)

                self.writer.set_step((epoch - 1) * len(self.valid_data_loader) + batch_idx, 'valid')
                self.valid_metrics.update('loss', loss.item())

                predict = (output >= 0.5)
                maxclass = torch.argmax(output, dim=1) # make sure every sentence predicted to at least one class
                for i in range(len(predict)):
                    predict[i][maxclass[i].item()] = 1
                predict = predict.type(torch.LongTensor).to(self.device)

                for met in self.metric_ftns:
                    self.valid_metrics.update(met.__name__, met(predict, target))
                #self.writer.add_image('input', make_grid(data.cpu(), nrow=8, normalize=True))

        # add histogram of model parameters to the tensorboard
        for name, p in self.model.named_parameters():
            self.writer.add_histogram(name, p, bins='auto')
        return self.valid_metrics.result()

    def _progress(self, batch_idx):
        base = '[{}/{} ({:.0f}%)]'
        if hasattr(self.data_loader, 'n_samples'):
            current = batch_idx * self.data_loader.batch_size
            total = self.data_loader.n_samples
        else:
            current = batch_idx
            total = self.len_epoch
        return base.format(current, total, 100.0 * current / total)


