# EXP-61 — `--check` 的逐格断言与"改一格必红"

## 假设

`--check` 对 array 展开后的每个对象都要独立断言属性（不是抽查对象总数）。
若成立，则改动任意一格的任意属性都必须 exit 1，且输出里**指名到 `{id}_r{i}c{j}`
与具体属性名**；未改动时 0 mismatch。

## 判据

- 正例：3×3 阵列 check → `mismatches=0`，`checked` 等于逐格属性总数。
- 负例①：把 spec 里第 (1,2) 格的 `d1` 改 10%，`--check` exit 1，且 bad 行 object 为
  `arr_r1c2`、property 含 `x span`/`y span`。
- 负例②：只把总对象数改成一样但打乱一格位置 → 仍必须被拦（证明不是只比计数）。

## 负对照

把 check 的 array 展开逻辑换成「只断言对象个数」（模拟 K11 那张代理属性错误），
负例①必须**变绿**（抓不到）。若删掉真检查后负例①仍是红的，说明红的原因不是这条检查，
判据无效。

## 命令

```bash
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec _scratch/regress/2026-11-11/array/spec_3x3_bad.json \
  --only-check _scratch/regress/2026-11-11/array/build/arr3.fsp --json; echo "exit=$?"
```

## 结论

（执行后补）
