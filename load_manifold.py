#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 09:47:42 2024

@author: fmry
"""

#%% Sources

#%% Modules

import jax.numpy as jnp
import jax.random as jrandom

import pandas as pd

from typing import Tuple

from geometry.manifolds import EllipticFinsler, PointcarreLeft, PointcarreRight, TimeOnly
from geometry.manifolds import ExpectedEllipticFinsler, ExpectedPointcarreLeft, ExpectedPointcarreRight
from geometry.manifolds import StochasticEllipticFinsler

#%% Load manifolds

def load_manifold(manifold:str="direction_only", 
                  ):
    
    if manifold == "direction_only":
        Malpha = EllipticFinsler(c1=lambda t,x,v: -1.5*jnp.cos(jnp.pi/2+6*jnp.pi/10),
                                 c2=lambda t,x,v: -1.5*jnp.sin(jnp.pi/2+6*jnp.pi/10), 
                                 a=lambda t,x,v: 2,
                                 b=lambda t,x,v: 2,
                                 theta=lambda t,x,v: jnp.pi,
                                 )
        Mbeta = EllipticFinsler(c1=lambda t,x,v: 3/4,
                                c2=lambda t,x,v: 0, 
                                a=lambda t,x,v: 1,
                                b=lambda t,x,v: 1,
                                theta=lambda t,x,v: 0,
                                )
        
        tack_metrics = [Malpha,Mbeta,Malpha,Mbeta,Malpha]
        reverse_tack_metrics = [Mbeta, Malpha, Mbeta, Malpha, Mbeta]
        
        t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
        z0 = jnp.array([0.,0.], dtype=jnp.float32)
        zT = jnp.array([2.,8.], dtype=jnp.float32)
        
        return t0, z0, zT, tack_metrics, reverse_tack_metrics
    
    elif manifold == "time_only":

        Malpha = TimeOnly()
        Mbeta = EllipticFinsler(c1=lambda t,x,v: -1.5*jnp.cos(0.),
                                c2=lambda t,x,v: -1.5*jnp.sin(0.), 
                                a=lambda t,x,v: 7,
                                b=lambda t,x,v: 7./4,
                                theta=lambda t,x,v: jnp.pi/4,
                                )
        
        tack_metrics = [Malpha,Mbeta]
        reverse_tack_metrics = [Mbeta, Malpha]
        
        t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
        z0 = jnp.array([0.,0.], dtype=jnp.float32)
        zT = jnp.array([5*jnp.pi,0.], dtype=jnp.float32)
        
        return t0, z0, zT, tack_metrics, reverse_tack_metrics
    
    elif manifold == "poincarre":
        
        Malpha = PointcarreLeft(d=0.5)
        Mbeta = PointcarreRight(d=0.5)
        
        tack_metrics = [Malpha,Mbeta,Malpha,Mbeta,Malpha]
        reverse_tack_metrics = [Mbeta, Malpha, Mbeta, Malpha, Mbeta]
        
        k = 10.
        t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
        z0 = jnp.array([1.,1.], dtype=jnp.float32)
        zT = jnp.array([k,1.], dtype=jnp.float32)
        
        return t0, z0, zT, tack_metrics, reverse_tack_metrics
    
    else:
        raise ValueError(f"Manifold, {manifold}, is not defined. Only suported is: \n\t-Euclidean\n\t-Paraboloid\n\t-Sphere")
        
#%% Load Manifolds

def load_stochastic_manifold(manifold:str="direction_only", 
                             seed:int=2712,
                             N_sim:int=10,
                             ):
    
    key = jrandom.key(seed)
    key, subkey = jrandom.split(key)
    
    if manifold == "direction_only":
        
        sigma = 1.0
        
        eps = sigma*jrandom.normal(subkey, shape=(N_sim,2))
        
        Malpha = []
        Mbeta = []
        tack_metrics = []
        reverse_tack_metrics = []
        for e in eps:
            M1 = StochasticEllipticFinsler(eps=e[0],
                                           c1=lambda t,x,v,eps: -1.5*jnp.cos(jnp.pi/2+6*jnp.pi/10),
                                           c2=lambda t,x,v,eps: -1.5*jnp.sin(jnp.pi/2+6*jnp.pi/10), 
                                           a=lambda t,x,v,eps: 2,
                                           b=lambda t,x,v,eps: 2,
                                           theta=lambda t,x,v,eps: eps+jnp.pi,
                                           )
            M2 = StochasticEllipticFinsler(eps=e[1],
                                           c1=lambda t,x,v,eps: 3/4,
                                           c2=lambda t,x,v,eps: 0, 
                                           a=lambda t,x,v,eps: 1,
                                           b=lambda t,x,v,eps: 1,
                                           theta=lambda t,x,v,eps: eps+0,
                                           )
            
            Malpha.append(M1)
            Mbeta.append(M2)
        
        tack_metrics = [(m1, m2) for m1, m2 in zip(Malpha, Mbeta)]
        reverse_tack_metrics = [(m2, m1) for m1, m2 in zip(Malpha, Mbeta)]
        
        key, subkey = jrandom.split(key)
        eps = sigma*jrandom.normal(subkey, shape=(100,2))
        
        Malpha_expected = ExpectedEllipticFinsler(subkey, eps[:,0], 
                                                  c1=lambda t,x,v,eps: -1.5*jnp.cos(jnp.pi/2+6*jnp.pi/10),
                                                  c2=lambda t,x,v,eps: -1.5*jnp.sin(jnp.pi/2+6*jnp.pi/10), 
                                                  a=lambda t,x,v,eps: 2,
                                                  b=lambda t,x,v,eps: 2,
                                                  theta=lambda t,x,v,eps: eps+jnp.pi,
                                                  )
        Mbeta_expected = ExpectedEllipticFinsler(subkey, eps[:,1], 
                                                 c1=lambda t,x,v,eps: 3/4,
                                                 c2=lambda t,x,v,eps: 0, 
                                                 a=lambda t,x,v,eps: 1,
                                                 b=lambda t,x,v,eps: 1,
                                                 theta=lambda t,x,v,eps: eps+0,
                                                 )
        
        t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
        z0 = jnp.array([0.,0.], dtype=jnp.float32)
        zT = jnp.array([2.,8.], dtype=jnp.float32)
        
        return t0, z0, zT, Malpha_expected, Mbeta_expected, tack_metrics, reverse_tack_metrics
    
    elif manifold == "time_only":
        
        sigma = 1.0
        
        eps = sigma*jrandom.normal(subkey, shape=(N_sim,))
        
        Malpha = []
        Mbeta = []
        tack_metrics = []
        reverse_tack_metrics = []
        for e in eps:
            M1 = TimeOnly()
            M2 = StochasticEllipticFinsler(eps=e,
                                           c1=lambda t,x,v,eps: -1.5,
                                           c2=lambda t,x,v,eps: 0., 
                                           a=lambda t,x,v,eps: 7.,
                                           b=lambda t,x,v,eps: 7./4,
                                           theta=lambda t,x,v,eps: eps+jnp.pi/4,
                                           )
          
            Malpha.append(M1)
            Mbeta.append(M2) 
            
        tack_metrics = [(m1, m2) for m1, m2 in zip(Malpha, Mbeta)]
        reverse_tack_metrics = [(m2, m1) for m1, m2 in zip(Malpha, Mbeta)]
        
        key, subkey = jrandom.split(key)
        eps = sigma*jrandom.normal(subkey, shape=(100,))
        
        Malpha_expected = TimeOnly()
        Mbeta_expected = ExpectedEllipticFinsler(subkey, eps, 
                                                 c1=lambda t,x,v,eps: -1.5,
                                                 c2=lambda t,x,v,eps: 0., 
                                                 a=lambda t,x,v,eps: 7.,
                                                 b=lambda t,x,v,eps: 7./4,
                                                 theta=lambda t,x,v,eps: eps+jnp.pi/4,
                                                 )
        
        t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
        z0 = jnp.array([0.,0.], dtype=jnp.float32)
        zT = jnp.array([5*jnp.pi,0.], dtype=jnp.float32)
        
        return t0, z0, zT, Malpha_expected, Mbeta_expected, tack_metrics, reverse_tack_metrics
    
    elif manifold == "poincarre":
        
        eps = jrandom.uniform(subkey, shape=(N_sim,2), minval=0.4, maxval=0.6)
        
        Malpha = []
        Mbeta = []
        tack_metrics = []
        reverse_tack_metrics = []
        for e in eps:
            M1 = PointcarreLeft(d=e[0])
            M2 = PointcarreRight(d=e[1])
            
            Malpha.append(M1)
            Mbeta.append(M2)
            
        tack_metrics = [(m1, m2) for m1, m2 in zip(Malpha, Mbeta)]
        reverse_tack_metrics = [(m2, m1) for m1, m2 in zip(Malpha, Mbeta)]

        key, subkey = jrandom.split(key)
        eps = jrandom.uniform(subkey, shape=(100,2), minval=0.4, maxval=0.6)
        Malpha_expected = ExpectedPointcarreLeft(subkey, eps[:,0])
        Mbeta_expected = ExpectedPointcarreRight(subkey, eps[:,1])
        
        k = 10.
        t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
        z0 = jnp.array([1.,1.], dtype=jnp.float32)
        zT = jnp.array([k,1.], dtype=jnp.float32)
        
        return t0, z0, zT, Malpha_expected, Mbeta_expected, tack_metrics, reverse_tack_metrics
    
    else:
        raise ValueError(f"Manifold, {manifold}, is not defined. Only suported is: \n\t-Euclidean\n\t-Paraboloid\n\t-Sphere")
        
#%% Load Albatross data

def load_albatross_data(file_path:str = '../../../../Data/albatross/tracking_data.xls', 
                        )->Tuple:
    
    albatross_data = pd.read_excel(file_path)
    bird_idx = [0,25,50]
    data_idx = {bird_idx[0]: [[67,90], [149, 195], [315, 335]],
                bird_idx[1]: [[30, 40], [115, 140], [140, 160]],
                bird_idx[2]: [[15, 35], [92, 108], [325, 370]],
                }
    
    track_id = albatross_data["TRACKID"].unique()
    time_data = []
    w1 = []
    w2 = []
    x1 = []
    x2 = []
    for id_val in track_id:
        dummy_data = albatross_data[albatross_data['TRACKID']==id_val].reset_index()
        t = pd.to_datetime(dummy_data['YMDHMS'], format='%Y%m%d%H%M%S')
        t = t-t.loc[0]
        time_data.append(jnp.array(t.dt.total_seconds().to_numpy()).squeeze()/3600)
        w1.append(jnp.array([dummy_data['WND_SPD_MS_5'].to_numpy()]).squeeze()*jnp.cos(dummy_data['WND_DIR'].to_numpy()/(2*jnp.pi)))
        w2.append(jnp.array([dummy_data['WND_SPD_MS_5'].to_numpy()]).squeeze()*jnp.sin(dummy_data['WND_DIR'].to_numpy()/(2*jnp.pi)))
        x1.append(jnp.array([dummy_data['LATITUDE'].to_numpy()]).squeeze())
        x2.append(jnp.array([dummy_data['LONGITUDE'].to_numpy()]).squeeze())
        
    x_data = [jnp.vstack((y1,y2)).T for y1,y2 in zip(x1,x2)]
    w_data = [jnp.vstack((y1,y2)).T for y1,y2 in zip(w1,w2)]
    
    return x_data, w_data, data_idx

#%% Load Albatross Metrics

def load_albatross_metrics(manifold:str = "poincarre",
                           file_path:str = '../../../../Data/albatross/tracking_data.xls', 
                           N_sim:int=5,
                           seed:int=2712,
                           ):
    
    x_data, _ , data_idx = load_albatross_data(file_path)

    t0 = jnp.zeros(1, dtype=jnp.float32).squeeze()
    z0 = [x_data[b_idx][idx_val[0]] for b_idx,vals in data_idx.items() for idx_val in vals]
    zT = [x_data[b_idx][idx_val[1]] for b_idx,vals in data_idx.items() for idx_val in vals]
    
    key = jrandom.key(seed)
    key, subkey = jrandom.split(key)
    
    v_min = 0.0
    v_max = 20.0
    v_mean= v_max/2
    v_slope = 0.25

    frac_fun = lambda v: v_min/v_max+1.0/(1+jnp.exp(-v_slope*(jnp.linalg.norm(v)-v_mean)))
    
    if manifold == "direction_only":
        
        sigma = 1.0

        eps = sigma*jrandom.normal(subkey, shape=(N_sim,2))
        
        Malpha_stoch = []
        Mbeta_stoch = []
        tack_metrics = []
        reverse_tack_metrics = []
        for e in eps:
            M1 = StochasticEllipticFinsler(eps=e[0],
                                           c1=lambda t,x,v,eps: frac_fun(v)*jnp.linalg.norm(v),
                                           c2=lambda t,x,v,eps: -frac_fun(v)*jnp.linalg.norm(v)*jnp.sqrt((1-frac_fun(v)**2)), 
                                           a=lambda t,x,v,eps: jnp.linalg.norm(v),
                                           b=lambda t,x,v,eps: jnp.linalg.norm(v),
                                           theta=lambda t,x,v,eps: eps+(jnp.pi/2-jnp.arctan(v[1]/v[0])),
                                           )

            M2 = StochasticEllipticFinsler(eps=e[1],
                                           c1=lambda t,x,v,eps: -frac_fun(v)*jnp.linalg.norm(v),
                                           c2=lambda t,x,v,eps: -frac_fun(v)*jnp.linalg.norm(v)*jnp.sqrt((1-frac_fun(v)**2)), 
                                           a=lambda t,x,v,eps: jnp.linalg.norm(v),
                                           b=lambda t,x,v,eps: jnp.linalg.norm(v),
                                           theta=lambda t,x,v,eps: eps+(jnp.pi/2-jnp.arctan(v[1]/v[0])),
                                           )
            
            Malpha_stoch.append(M1)
            Mbeta_stoch.append(M2)
            
            tack_metrics.append([M1, M2])
            reverse_tack_metrics.append([M2, M1])

        Malpha = EllipticFinsler(c1=lambda t,x,v: frac_fun(v)*jnp.linalg.norm(v),
                                 c2=lambda t,x,v: -frac_fun(v)*jnp.linalg.norm(v)*jnp.sqrt((1-frac_fun(v)**2)), 
                                 a=lambda t,x,v: jnp.linalg.norm(v),
                                 b=lambda t,x,v: jnp.linalg.norm(v),
                                 theta=lambda t,x,v: (jnp.pi/2-jnp.arctan(v[1]/v[0]))#-jnp.pi/4,
                                 )
        Mbeta = EllipticFinsler(c1=lambda t,x,v: -frac_fun(v)*jnp.linalg.norm(v),
                                c2=lambda t,x,v: -frac_fun(v)*jnp.linalg.norm(v)*jnp.sqrt((1-frac_fun(v)**2)), 
                                a=lambda t,x,v: jnp.linalg.norm(v),
                                b=lambda t,x,v: jnp.linalg.norm(v),
                                theta=lambda t,x,v: (jnp.pi/2-jnp.arctan(v[1]/v[0]))#-jnp.pi/4,
                                )
        
        return t0, z0, zT, Malpha, Mbeta, tack_metrics, reverse_tack_metrics
    
    elif manifold == "time_only":
        
        sigma = 1.0
        
        eps = sigma*jrandom.normal(subkey, shape=(N_sim,))
        
        Malpha = []
        Mbeta = []
        tack_metrics = []
        reverse_tack_metrics = []
        for e in eps:
            M1 = TimeOnly()
            M2 = StochasticEllipticFinsler(eps=e,
                                           c1=lambda t,x,v,eps: -frac_fun(v)*jnp.linalg.norm(v),
                                           c2=lambda t,x,v,eps: -frac_fun(v)*jnp.linalg.norm(v)*jnp.sqrt((1-frac_fun(v)**2)), 
                                           a=lambda t,x,v,eps: jnp.linalg.norm(v),
                                           b=lambda t,x,v,eps: jnp.linalg.norm(v),
                                           theta=lambda t,x,v,eps: eps+(jnp.pi/2-jnp.arctan(v[1]/v[0])),
                                           )
            
            Malpha.append(M1)
            Mbeta.append(M2)
            
            tack_metrics.append([M1, M2])
            reverse_tack_metrics.append([M2, M1])
          
            Malpha.append(M1)
            Mbeta.append(M2) 
        
        
        key, subkey = jrandom.split(key)
        eps = jrandom.uniform(subkey, shape=(100,), minval=-0.5, maxval=0.5)
        
        Malpha = TimeOnly()
        Mbeta = EllipticFinsler(c1=lambda t,x,v: -frac_fun(v)*jnp.linalg.norm(v),
                                c2=lambda t,x,v: -frac_fun(v)*jnp.linalg.norm(v)*jnp.sqrt((1-frac_fun(v)**2)), 
                                a=lambda t,x,v: jnp.linalg.norm(v),
                                b=lambda t,x,v: jnp.linalg.norm(v),
                                theta=lambda t,x,v: (jnp.pi/2-jnp.arctan(v[1]/v[0]))#-jnp.pi/4,
                                )
        
        return t0, z0, zT, Malpha, Mbeta, tack_metrics, reverse_tack_metrics
    
    elif manifold == "poincarre":
        
        eps = jrandom.uniform(subkey, shape=(N_sim,2), minval=0.4, maxval=0.6)
        
        Malpha = []
        Mbeta = []
        tack_metrics = []
        reverse_tack_metrics = []
        for e in eps:
            M1 = PointcarreLeft(d=e[0])
            M2 = PointcarreRight(d=e[1])
            
            Malpha.append(M1)
            Mbeta.append(M2)
            
            tack_metrics.append([M1, M2])
            reverse_tack_metrics.append([M2, M1])

        Malpha = PointcarreLeft(d=0.5)
        Mbeta = PointcarreRight(d=0.5)
        
        return t0, z0, zT, Malpha, Mbeta, tack_metrics, reverse_tack_metrics
    
    return