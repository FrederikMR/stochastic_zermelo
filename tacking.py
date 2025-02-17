#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 30 12:52:36 2024

@author: fmry
"""

#%% Sources

#https://jax.readthedocs.io/en/latest/faq.html

#%% Modules

import jax.numpy as jnp
from jax import jit, vmap

import timeit

import os

import pickle

#argparse
import argparse

from typing import Dict

from load_manifold import load_manifold, load_stochastic_manifold, load_albatross_metrics

from geometry.geodesic import GEORCE_H
from geometry.tacking import SequentialOptimizationADAM, SequentialOptimizationBFGS

#%% Args Parser

def parse_args():
    parser = argparse.ArgumentParser()
    # File-paths
    parser.add_argument('--manifold', default="direction_only",
                        type=str)
    parser.add_argument('--geometry', default="stochastic",
                        type=str)
    parser.add_argument('--method', default="adam",
                        type=str)
    parser.add_argument('--T', default=1_000,
                        type=int)
    parser.add_argument('--lr_rate', default=0.01,
                        type=float)
    parser.add_argument('--tol', default=1e-2,
                        type=float)
    parser.add_argument('--max_iter', default=1,
                        type=int)
    parser.add_argument('--sub_iter', default=5,
                        type=int)
    parser.add_argument('--N_sim', default=5,
                        type=int)
    parser.add_argument('--data_idx', default=0,
                        type=int)
    parser.add_argument('--seed', default=2712,
                        type=int)
    parser.add_argument('--albatross_file_path', default='../../../../Data/albatross/tracking_data.xls',
                        type=str)
    parser.add_argument('--save_path', default='tacking_local/',
                        type=str)

    args = parser.parse_args()
    return args

#%% Timing

def estimate_method(Geodesic, z0, zT, M, base_length=None):
    
    args = parse_args()
    
    method = {} 
    print("Computing Estimates")
    zt, grad, grad_idx = Geodesic(z0,zT)
    print("\t-Estimate Computed")
    timing = []
    timing = timeit.repeat(lambda: Geodesic(z0,zT)[0].block_until_ready(), 
                           number=args.number_repeats, 
                           repeat=args.timing_repeats)
    print("\t-Timing Computed")
    timing = jnp.stack(timing)
    length = M.length(zt)
    method['grad_norm'] = jnp.linalg.norm(grad)
    method['length'] = length
    method['iterations'] = grad_idx
    method['mu_time'] = jnp.mean(timing)
    method['std_time'] = jnp.std(timing)
    method['tol'] = args.tol
    method['max_iter'] = args.max_iter
    
    if base_length is None:
        method['error'] = None
    else:
        method['error'] = jnp.abs(length-base_length)
    
    return method

#%% Curve Estimation

def estimate_curve(CurveMethod, t0, z0, zT):
    
    method_curve = {}    
    ts, zs, grad, idx = CurveMethod(t0, z0, zT)
    method_curve['travel_time'] = ts[-1]
    method_curve['zs'] = zs
    method_curve['grad_norm'] = jnp.linalg.norm(grad)
    method_curve['idx'] = idx
    
    print(f"Travel time = {ts[-1]:.4f}")
    
    return method_curve


#%% Save times

def save_times(methods:Dict, save_path:str)->None:
    
    with open(save_path, 'wb') as f:
        pickle.dump(methods, f)
    
    return

#%% Riemannian Run Time code

def estimate_tacking()->None:
    
    args = parse_args()
    
    save_path = ''.join((args.save_path, f'deterministic/{args.manifold}/'))
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        
    save_path = ''.join((save_path, args.method, 
                         f'_{args.manifold}.pkl', 
                         ))
    if os.path.exists(save_path):
        os.remove(save_path)
    
    t0, z0, zT, tack_metrics, reverse_tack_metrics = load_manifold(args.manifold)
    
    Geodesic = GEORCE_H(tack_metrics[0], init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
    ReverseGeodesic = GEORCE_H(reverse_tack_metrics[0], init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
    
    if args.method == "adam":
        Tacking = SequentialOptimizationADAM(tack_metrics, lr_rate=args.lr_rate, init_fun=None, max_iter=args.max_iter, 
                                         tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        ReverseTacking = SequentialOptimizationADAM(reverse_tack_metrics, lr_rate = args.lr_rate, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                    T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
    elif args.method == "bfgs":
        Tacking = SequentialOptimizationBFGS(tack_metrics, init_fun=None, max_iter=args.max_iter, 
                                     tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        ReverseTacking = SequentialOptimizationBFGS(reverse_tack_metrics, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                    T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
    else:
        raise ValueError("Invalid method for sequential optimization!")
        
        
    methods = {}
    
    print("Estimation of Geodesics...")
    methods['Geodesic'] = estimate_curve(jit(Geodesic), t0, z0, zT)
    methods['ReverseGeodesic'] = estimate_curve(jit(ReverseGeodesic), t0, z0, zT)
    
    for i in range(1, len(tack_metrics)):
        print(f"Estimation {i} tack points...")
        methods[f'Tacking_{i}'] = estimate_curve(jit(lambda t0, z0, zT: Tacking(t0, z0, zT, n_tacks=i)), 
                                                 t0, z0, zT)
        methods[f'ReverseTacking_{i}'] = estimate_curve(jit(lambda t0, z0, zT: ReverseTacking(t0, z0, zT, n_tacks=i)), 
                                                        t0, z0, zT)
        save_times(methods, save_path)
        
    return

#%% Riemannian Run Time code

def estimate_stochastic_tacking()->None:
    
    args = parse_args()
    
    save_path = ''.join((args.save_path, f'stochastic/{args.manifold}/'))
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        
    save_path = ''.join((save_path, args.method, 
                         f'_{args.manifold}.pkl', 
                         ))
    if os.path.exists(save_path):
        os.remove(save_path)
    
    t0, z0, zT, Malpha_expected, Mbeta_expected, tack_metrics_sim, reverse_tack_metrics_sim = load_stochastic_manifold(args.manifold,
                                                                                                                       N_sim=args.N_sim,
                                                                                                                       seed=args.seed)
    
    N_sim = len(tack_metrics_sim)
    
    methods = {}
    Geodesic = GEORCE_H(Malpha_expected, init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
    ReverseGeodesic = GEORCE_H(Mbeta_expected, init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
    
    
    print("Estimation of Expected Geodesics...")
    methods['ExpectedGeodesic'] = estimate_curve(jit(Geodesic), t0, z0, zT)
    methods['ExpectedReverseGeodesic'] = estimate_curve(jit(ReverseGeodesic), t0, z0, zT)
    
    if args.method == "adam":
        Tacking = SequentialOptimizationADAM([Malpha_expected, Mbeta_expected], lr_rate=args.lr_rate, init_fun=None, max_iter=args.max_iter, 
                                         tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        ReverseTacking = SequentialOptimizationADAM([Mbeta_expected, Malpha_expected], lr_rate = args.lr_rate, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                    T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
    elif args.method == "bfgs":
        Tacking = SequentialOptimizationBFGS([Malpha_expected, Mbeta_expected], init_fun=None, max_iter=args.max_iter, 
                                     tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        ReverseTacking = SequentialOptimizationBFGS([Mbeta_expected, Malpha_expected], init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                    T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
    else:
        raise ValueError("Invalid method for sequential optimization!")
        
    save_times(methods, save_path)
        
    print("Estimation of expected tack points...")
    methods['ExpectedTacking'] = estimate_curve(jit(lambda t0, z0, zT: Tacking(t0, z0, zT, n_tacks=1)), 
                                             t0, z0, zT)
    methods['ExpectedReverseTacking'] = estimate_curve(jit(lambda t0, z0, zT: ReverseTacking(t0, z0, zT, n_tacks=1)), 
                                                    t0, z0, zT)
    save_times(methods, save_path)
    
    for i in range(N_sim):
        print(f"Computing curves for simulation {i+1}/{N_sim}...")
        
        tack_metrics = tack_metrics_sim[i]
        reverse_tack_metrics = reverse_tack_metrics_sim[i]

        Geodesic = GEORCE_H(tack_metrics[0], init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
        ReverseGeodesic = GEORCE_H(reverse_tack_metrics[0], init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
        
        if args.method == "adam":
            Tacking = SequentialOptimizationADAM(tack_metrics, lr_rate=args.lr_rate, init_fun=None, max_iter=args.max_iter, 
                                             tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
            ReverseTacking = SequentialOptimizationADAM(reverse_tack_metrics, lr_rate = args.lr_rate, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                        T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        elif args.method == "bfgs":
            Tacking = SequentialOptimizationBFGS(tack_metrics, init_fun=None, max_iter=args.max_iter, 
                                         tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
            ReverseTacking = SequentialOptimizationBFGS(reverse_tack_metrics, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                        T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        else:
            raise ValueError("Invalid method for sequential optimization!")
        
        print("\tEstimation of Geodesics...")
        methods[f'Geodesic{i}'] = estimate_curve(jit(Geodesic), t0, z0, zT)
        methods[f'ReverseGeodesic{i}'] = estimate_curve(jit(ReverseGeodesic), t0, z0, zT)
        
        for j in range(1, len(tack_metrics)):
            print(f"\tEstimation {j} tack points...")
            methods[f'Tacking{i}_{j}'] = estimate_curve(jit(lambda t0, z0, zT: Tacking(t0, z0, zT, n_tacks=j)), 
                                                     t0, z0, zT)
            methods[f'ReverseTacking{i}_{j}'] = estimate_curve(jit(lambda t0, z0, zT: ReverseTacking(t0, z0, zT, n_tacks=j)), 
                                                            t0, z0, zT)
            save_times(methods, save_path)
            
    return

#%% Riemannian Run Time code

def estimate_albatross_tacking()->None:
    
    args = parse_args()
    
    save_path = ''.join((args.save_path, f'albatross/{args.manifold}/'))
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        
    save_path = ''.join((save_path, args.method, 
                         f'_{args.manifold}.pkl', 
                         ))
    if os.path.exists(save_path):
        os.remove(save_path)
    
    t0, z0, zT, Malpha, Mbeta, tack_metrics_sim, reverse_tack_metrics_sim = load_albatross_metrics(args.manifold,
                                                                                                   file_path=args.albatross_file_path,
                                                                                                   N_sim=args.N_sim,
                                                                                                   seed=args.seed,
                                                                                                   )
    z0 = z0[args.data_idx]
    zT = zT[args.data_idx]
    
    N_sim = len(tack_metrics_sim)
    
    methods = {}
    Geodesic = GEORCE_H(Malpha, init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
    ReverseGeodesic = GEORCE_H(Mbeta, init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
    
    print("Estimation of Geodesics...")
    methods['Geodesic'] = estimate_curve(jit(Geodesic), t0, z0, zT)
    methods['ReverseGeodesic'] = estimate_curve(jit(ReverseGeodesic), t0, z0, zT)
    
    if args.method == "adam":
        Tacking = SequentialOptimizationADAM([Malpha, Mbeta], lr_rate=args.lr_rate, init_fun=None, max_iter=args.max_iter, 
                                         tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        ReverseTacking = SequentialOptimizationADAM([Mbeta, Malpha], lr_rate = args.lr_rate, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                    T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
    elif args.method == "bfgs":
        Tacking = SequentialOptimizationBFGS([Malpha, Mbeta], init_fun=None, max_iter=args.max_iter, 
                                     tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        ReverseTacking = SequentialOptimizationBFGS([Mbeta, Malpha], init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                    T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
    else:
        raise ValueError("Invalid method for sequential optimization!")
        
    print("Estimation of tack points...")
    methods['Tacking'] = estimate_curve(jit(lambda t0, z0, zT: Tacking(t0, z0, zT, n_tacks=1)), 
                                             t0, z0, zT)
    methods['ReverseTacking'] = estimate_curve(jit(lambda t0, z0, zT: ReverseTacking(t0, z0, zT, n_tacks=1)), 
                                                    t0, z0, zT)
    save_times(methods, save_path)
    
    for i in range(N_sim):
        print(f"Computing curves for simulation {i+1}/{N_sim}...")
        
        tack_metrics = tack_metrics_sim[i]
        reverse_tack_metrics = reverse_tack_metrics_sim[i]

        Geodesic = GEORCE_H(tack_metrics[0], init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
        ReverseGeodesic = GEORCE_H(reverse_tack_metrics[0], init_fun=None, T=args.T, tol=args.tol, max_iter=args.max_iter, line_search_params={'rho': 0.5})
        
        if args.method == "adam":
            Tacking = SequentialOptimizationADAM(tack_metrics, lr_rate=args.lr_rate, init_fun=None, max_iter=args.max_iter, 
                                             tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
            ReverseTacking = SequentialOptimizationADAM(reverse_tack_metrics, lr_rate = args.lr_rate, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                        T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        elif args.method == "bfgs":
            Tacking = SequentialOptimizationBFGS(tack_metrics, init_fun=None, max_iter=args.max_iter, 
                                         tol=args.tol, T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
            ReverseTacking = SequentialOptimizationBFGS(reverse_tack_metrics, init_fun = None, max_iter=args.max_iter, tol=args.tol,
                                                        T=args.T, sub_iter=args.sub_iter, line_search_params={'rho': 0.5})
        else:
            raise ValueError("Invalid method for sequential optimization!")
        
        print("\tEstimation of Geodesics...")
        methods[f'Geodesic{i}'] = estimate_curve(jit(Geodesic), t0, z0, zT)
        methods[f'ReverseGeodesic{i}'] = estimate_curve(jit(ReverseGeodesic), t0, z0, zT)
        
        for j in range(1, len(tack_metrics)):
            print(f"\tEstimation {j} tack points...")
            methods[f'Tacking{i}_{j}'] = estimate_curve(jit(lambda t0, z0, zT: Tacking(t0, z0, zT, n_tacks=j)), 
                                                     t0, z0, zT)
            methods[f'ReverseTacking{i}_{j}'] = estimate_curve(jit(lambda t0, z0, zT: ReverseTacking(t0, z0, zT, n_tacks=j)), 
                                                            t0, z0, zT)
            save_times(methods, save_path)
            
    return

#%% main

if __name__ == '__main__':
    
    args = parse_args()
    
    if args.geometry == "fixed":
        estimate_tacking()
    elif args.geometry == "stochastic":
        estimate_stochastic_tacking()
    elif args.geometry == "albatross":
        estimate_albatross_tacking()
    else:
        raise ValueError("Invalid geometry for runtime comparison.")