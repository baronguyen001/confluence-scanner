# Walk-Forward Guide

A single train/test split is easy to overfit. Walk-forward validation repeats the discipline:

1. Train or tune on a historical window.
2. Validate only on data that starts after the training window.
3. Step forward and repeat.
4. Compare train rank versus validation rank.

`walk_forward_split` enforces `train.index.max() < val.index.min()` for every fold. The helper `classify_robustness()` labels a candidate as strong, robust, overfit, an underperformer, or weak on both windows.

The examples use generic EMA-cross candidates because the point is the workflow, not a secret parameter set. Replace the candidates with your own research dimensions, then keep only ideas that survive out-of-sample.
