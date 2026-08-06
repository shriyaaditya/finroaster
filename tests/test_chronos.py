import torch
import pandas as pd
from chronos import ChronosPipeline

print("Loading Chronos model...")
pipeline = ChronosPipeline.from_pretrained(
    "amazon/chronos-t5-small",
    device_map="cpu",
    torch_dtype=torch.float32,
)

# Create a small toy time series (spend per day)
context = torch.tensor([10.5, 12.0, 15.0, 8.0, 20.0, 14.5, 18.0, 22.0, 19.5, 25.0])
print("Executing 14-day forecast...")
forecast = pipeline.predict(context, prediction_length=14) # shape: [num_series, num_samples, prediction_length]

# Quantiles: 10th, 50th, 90th percentiles
import numpy as np
low, median, high = np.percentile(forecast[0].numpy(), [10, 50, 90], axis=0)

print("Forecast completed successfully:")
print("p10:", low)
print("p50:", median)
print("p90:", high)
