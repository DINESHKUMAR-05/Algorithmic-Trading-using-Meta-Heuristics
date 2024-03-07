from torch import optim
import numpy as np
import gc
import random
import os
from src.genetic_algorithm import seed_everything
from src.models import *
from pyswarm import pso
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:2"

class PSO:
  def __init__(self,swarmsize: int = 100, omega: int = 0.5, maxiter: int = 100,device,criterion,model: str,X_val,y_val):
    self.swarmsize= swarmsize
    self.omega = omega
    self.maxiter = maxiter
    self.model=model
    self.device=device
    self.criterion = criterion
    self.X_val = X_val
    self.y_val = y_val

  def objFn(self,params):
    lr = params[0]
    epoch = params[1]
    hidden_units = params[2]
    num_layers = params[3]
    if self.model == 'LSTM':
        seed_everything(77)
        model = LSTM(input_size=self.X_val.shape[2],
                hidden_size=hidden_units,
                num_layers=num_layers).to(self.device)
      
    elif self.model == 'GRU':
      seed_everything(77)
      model = GRU(input_size=self.X_val.shape[2],
              hidden_size=hidden_units,
              num_layers=num_layers).to(self.device)
        
    else:
      raise ValueError('Only LSTM and GRU blocks are available for optimization.')


    optimizer = optim.Adam(model.parameters(), lr=lr)
    seed_everything(77)
    train(self.model, self.criterion, optimizer, self.device, self.X_val, self.y_val, epoch, 
          verbose=False, return_loss_history=False, compute_test_loss=False)
          
    return predict(self.model, self.X_val, self.y_val, self.criterion, self.device)
  
  def fit(self,lb,ub):
    return pso(self.objFn, lower_bound=lb, upper_bound=ub)