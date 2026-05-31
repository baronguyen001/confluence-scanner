# Walk-Forward Demo

The notebook uses the offline fixture in `tests/fixtures/btc_4h_sample.csv`.

It demonstrates:

- rolling train/validation folds,
- no-leakage boundaries,
- in-sample versus out-of-sample metric divergence,
- and robustness labels.

Run:

```bash
papermill examples/walk_forward_demo/notebook.ipynb /tmp/wf_out.ipynb
```
