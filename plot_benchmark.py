import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("benchmark.csv")

plt.figure(figsize=(10, 5))
plt.plot(df["entities"], df["min"], label="min")
plt.plot(df["entities"], df["avg"], label="avg")
plt.plot(df["entities"], df["max"], label="max")

# Reference line at y = 1/60
plt.axhline(y=1/500, linestyle="--", linewidth=1, label="1/500")

plt.xlabel("Entities")
plt.ylabel("Value")
plt.title("Benchmark Results")
plt.legend()
plt.xticks(rotation=45, ha="right")

plt.tight_layout()
plt.savefig("benchmark.png")
