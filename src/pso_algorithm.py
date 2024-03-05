import numpy as np
import random
import os
from dataclasses import dataclass
from src.models import *  # Assuming your models are defined in src.models
from torch import optim
import torch
from src.genetic_algorithm import seed_everything

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:2"

@dataclass
class PSOConfig:
    num_particles: int = 20
    num_epochs: int = 10
    inertia_weight: float = 0.5
    cognitive_weight: float = 1.5
    social_weight: float = 2.0
    max_velocity: float = 0.1

class Individual:
    def __init__(self):
        self.num_epochs = np.random.choice(np.arange(60, 300))
        self.hidden_size = np.random.choice([2 ** power for power in range(2, 10)])
        self.num_layers = np.random.choice(np.arange(2, 15))
        self.learning_rate = round(np.random.random(), 2)
        self.loss = np.inf
        self.position = np.array([self.hidden_size, self.num_layers, self.learning_rate, self.num_epochs])
        self.velocity = np.zeros_like(self.position)
        self.best_position = np.copy(self.position)  # Initialize best_position attribute

    def __repr__(self):
        return (f"loss: {self.loss:.4}, "
                f"hidden_size: {self.hidden_size}, num_layers: {self.num_layers}, "
                f"learning_rate: {self.learning_rate}, num_epochs: {self.num_epochs}")

@dataclass
class PopulationPSO:
    def __init__(self, config: PSOConfig):
        self.individuals = [Individual() for _ in range(config.num_particles)]
        self.best_individual = min(self.individuals, key=lambda x: x.loss).position

class PSO:
    def __init__(self, optimized_block, criterion, population: PopulationPSO, config: PSOConfig, device, verbose=True, seed: int = 77):
        self.optimized_block = optimized_block
        self.criterion = criterion
        self.population = population
        self.config = config
        self.device = device
        self.verbose = verbose
        self.seed = seed
        self.val_loss_history = []

    def fit(self, X_val, y_val):
        for epoch in range(self.config.num_epochs):
            self.evaluate(X_val, y_val)
            self.update_best_individual()
            self.val_loss_history.append(self.population.best_individual.loss)
            for individual in self.population.individuals:
                self.update_velocity(individual)
                self.update_position(individual)
            if self.verbose:
                clear_output(wait=True)
                print(f"Epoch: {epoch + 1}")
                plot_metric(self.criterion.__class__.__name__, 
                            val_metric=self.val_loss_history)
                print(f'{self.population.best_indivdual}')
                print(f"Epoch: {epoch + 1}, Best Individual: {self.population.best_individual}")

    def evaluate(self, X_val, y_val):
        for individual in self.population.individuals:
            model = self.create_model(individual,X_val,y_val)
            optimizer = optim.Adam(model.parameters(), lr=individual.learning_rate)
            train(model, self.criterion, optimizer, device, X_val, y_val, individual.num_epochs, verbose=False, return_loss_history=False, compute_test_loss=False)
            individual.loss = predict(model, X_val, y_val, self.criterion, device)
            del model

    def create_model(self, individual, X_val, y_val):
        seed_everything(self.seed)
        if self.optimized_block == 'LSTM':
            model = LSTM(input_size=X_val.shape[2], hidden_size=int(individual.hidden_size), num_layers=individual.num_layers).to(self.device)
        elif self.optimized_block == 'GRU':
            model = GRU(input_size=X_val.shape[2], hidden_size=int(individual.hidden_size), num_layers=individual.num_layers).to(self.device)
        else:
            raise ValueError('Only LSTM and GRU blocks are available for optimization.')
        return model

    def update_best_individual(self):
        self.population.best_individual = min(self.population.individuals, key=lambda x: x.loss)

    def update_velocity(self, individual):
        inertia_term = self.config.inertia_weight * individual.velocity
        cognitive_term = self.config.cognitive_weight * np.random.rand() * (individual.best_position - individual.position)
        social_term = self.config.social_weight * np.random.rand() * (self.population.best_individual.position - individual.position)
        individual.velocity = inertia_term + cognitive_term + social_term
        individual.velocity = np.clip(individual.velocity, -self.config.max_velocity, self.config.max_velocity)

    def update_position(self, individual):
        individual.position += individual.velocity
        individual.hidden_size = int(individual.position[0])
        individual.num_layers = int(individual.position[1])
        individual.learning_rate = individual.position[2]
        individual.num_epochs = int(individual.position[3])
        individual.hidden_size = np.clip(individual.hidden_size, 2 ** 2, 2 ** 9)
        individual.num_layers = np.clip(individual.num_layers, 2, 14)
        individual.learning_rate = np.clip(individual.learning_rate, 0.001, 1)
        individual.num_epochs = np.clip(individual.num_epochs, 10, 300)
