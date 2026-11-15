# Frozen 2019 selection before opening the 2022 test

The candidate code and the preregistered rule were run in `--validation-only` mode. The later-year file was not opened by that command. Western Iberia 2019 count WAPE on 1,880 matched cell-passes:

| Method | WAPE | MAE |
|---|---:|---:|
| Fixed ratio | 1.141744 | 0.664398 |
| VIIRS-only features | 0.757663 | 0.440896 |
| Monotone VIIRS-only features | 0.768266 | 0.447066 |
| Legacy features | **0.739874** | **0.430543** |

The preregistered choice for 2022 is **legacy**. The two VIIRS-only candidates are still evaluated and reported on 2022, but neither can be promoted under the preregistered 2019 selection rule. This result shows a real tradeoff: dropping a MODIS-derived matching-time feature reduces deployability dependence but slightly worsens validation accuracy in this conditional matched-pass sample. It does not validate an all-overpass VIIRS-only product.
