import pandas as pd
import numpy as np

def clean_dataframe(df):
    # Drop rows with >50% missing values
    threshold = len(df.columns) * 0.5
    df = df.dropna(thresh=threshold)
    
    # Fill numerical columns with median
    numerical_cols = df.select_dtypes(include=[np.number]).columns
    for col in numerical_cols:
        df[col].fillna(df[col].median(), inplace=True)
    
    # Fill categorical columns with mode
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        df[col].fillna(df[col].mode()[0], inplace=True)
    
    return df