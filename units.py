# units.py

FT_TO_M = 0.3048
KT_TO_MPS = 0.514444

def ft_to_m(ft):
    return ft * FT_TO_M

def m_to_ft(m):
    return m / FT_TO_M

def kt_to_mps(kt):
    return kt * KT_TO_MPS

def mps_to_kt(mps):
    return mps / KT_TO_MPS

def fpm_to_mps(fpm):
    return ft_to_m(fpm) / 60.0
