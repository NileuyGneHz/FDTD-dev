# P01 复现卡（2026-11-07）

> 结构化索引，供之后训练 / 修订 skills 使用。长表格、命令与推导见
> `notes/repro-2026-11-07-fsp-calibration.md` 与 `defects/D-001`、`D-002`，本卡不复制内容。
> 规则出处：`docs/constitution/reproduction-contract.md`；校验：`python tools/check_reproduction.py --case P01`。

```repro-card
{
  "case": "P01",
  "mode": "reproduce",
  "date": "2026-11-07",
  "target": {
    "quantity": "peak_absorption",
    "value": 0.97,
    "wavelength_um": 6.0,
    "source": "paper Fig.2(a) simulated R/T/A + experiment",
    "solver": "CST Microwave Studio 2009"
  },
  "actual_solver": "Lumerical FDTD v251",
  "locked": ["materials", "layer_stack", "topology", "geometry"],
  "numerics_aligned_from": "infrared_perfect_absorber.fsp",
  "truth_sources": [
    {
      "path": "model/infrared_perfect_absorber.fsp",
      "role": "reference",
      "converged": true,
      "shutoff": 8.87508e-06,
      "threshold": 1e-05,
      "p0_log": "model/infrared_perfect_absorber_p0.log",
      "peak_A": 0.8196,
      "peak_lam_um": 6.152
    },
    {
      "path": "model/d2_perfectCross.fsp",
      "role": "counterexample",
      "converged": false,
      "shutoff": 0.046734,
      "threshold": 1e-05,
      "p0_log": "model/d2_perfectCross_p0_course.log",
      "peak_A": null,
      "peak_lam_um": null
    }
  ],
  "runs": [
    {
      "name": "baseline",
      "out": "_scratch/regress/p01-20261107/baseline",
      "p0_log": "_scratch/regress/p01-20261107/baseline/point_00_base_p0.log",
      "shutoff_final": 8.77453e-05,
      "threshold": 0.0001,
      "peak_A": 0.8069,
      "peak_lam_um": 5.85
    },
    {
      "name": "fsp_calibrated",
      "out": "_scratch/regress/p01-20261107/fsp_calibrated",
      "p0_log": "_scratch/regress/p01-20261107/fsp_calibrated/point_00_base_p0.log",
      "shutoff_final": 9.52708e-06,
      "threshold": 1e-05,
      "peak_A": 0.8177,
      "peak_lam_um": 6.152
    }
  ],
  "same_input_regression": {
    "baseline_A": 0.8083,
    "repeat_A": 0.8069,
    "delta": 0.0014,
    "tolerance": 0.005
  },
  "excluded": [
    {
      "suspect": "边界条件",
      "verdict": "excluded",
      "evidence": "PML(x/y) 给 A=1.111 非物理；Periodic 给 0.808；notes/repro-2026-11-07-fsp-calibration.md §4",
      "rerun": "run_fdtd_sweep.py with spec_p01.json, bc=Periodic"
    },
    {
      "suspect": "网格",
      "verdict": "excluded",
      "evidence": "acc4 0.808 / acc6 0.801 / acc8 0.818，峰高变化 < 0.02",
      "rerun": "run_fdtd_sweep.py with mesh_accuracy 4/6/8"
    },
    {
      "suspect": "收敛",
      "verdict": "excluded",
      "evidence": "三条 _p0.log 末值 8.87508e-06 / 9.52708e-06 / 8.77453e-05 均小于各自阈值，且都有 Early termination",
      "rerun": "grep 'Early termination|Auto Shutoff' 三条 _p0.log"
    },
    {
      "suspect": "监视器 / 归一化 / 单位",
      "verdict": "excluded",
      "evidence": "T 约 -1.3e-05，R+T+A=1 自洽，源 amplitude=1",
      "rerun": "读 point_00_base.csv 校验 R+T+A"
    },
    {
      "suspect": "ts 量取面定义",
      "verdict": "excluded",
      "evidence": "两个课程 .fsp 层位 Al2O3 [-185,0] / 地 [-285,-185] / 十字 [0,100] nm 与 spec 逐层相同；functional_layers_match=true",
      "rerun": "inspect_fsp.py --config inspect_config.example.json --out _scratch/regress/fsp-20261107"
    },
    {
      "suspect": "材料实现",
      "verdict": "excluded",
      "evidence": "getindex 在 4/6/8/10 um 与 Drude 解析 (n,k) 逐位相同；6 um 为 n=2.8026 k=43.2457",
      "rerun": "_scratch/p01_material_probe.py（原型，未入库）"
    },
    {
      "suspect": "十字形状",
      "verdict": "excluded",
      "evidence": "论文 Fig.1(a) 高分辨率渲染为实心十字，与两个矩形叠加一致",
      "rerun": "pymupdf 以 3x 渲染 paper PDF 第 2 页"
    }
  ],
  "verdict": {
    "status": "solver_mismatch",
    "gap": 0.1504,
    "explainable_by": null,
    "stop_reason": "三条独立 Lumerical 结果在 6 um 处极差 0.0027，重建与课程工程峰值差 0.0018 且峰位相同；~0.82 是 Lumerical 在这套锁定参数下的稳定答案。论文 0.97 出自 CST 2009 仿真 + 实验，属求解器口径差异，不可由调参消除。继续追应换第二引擎（RCWA / 其他 FDTD）交叉验证，而非拟合 ts 到 120 nm。人做裁决。"
  },
  "defects": ["D-001", "D-002"],
  "training_items": [
    {
      "id": "R-001",
      "observation": "遍历 .fsp 对象树会改变 group scope，之后 getresult 报 Can not find object；同一会话必须先读已存谱再遍历树",
      "evidence": "三个工程全部触发；references/fsp-property-map.md §1",
      "destination": "references",
      "landed": true,
      "target_path": "skills/fdtd-lumerical-fsp-introspection/references/fsp-property-map.md"
    },
    {
      "id": "R-002",
      "observation": "同包多个 .fsp 必须逐个单独判 layoutmode + _p0.log 收敛，禁止合并成一个结论",
      "evidence": "defects/D-001：Periodic 版收敛 8.87508e-06，PML 版跑满 77813 步末值 0.046734",
      "destination": "SKILL.md",
      "landed": true,
      "target_path": "skills/fdtd-lumerical-fsp-introspection/SKILL.md"
    },
    {
      "id": "R-003",
      "observation": "数值 diff 用固定 1e-9 绝对下限会把 1 ps 判成等于 5 ps；改用相对容差 max(1e-18, |spec|*1e-6)，且 npts 应从 DFT 监视器读",
      "evidence": "journal/2026-11-07.md 第二轮；references/fsp-property-map.md §6",
      "destination": "references",
      "landed": true,
      "target_path": "skills/fdtd-lumerical-fsp-introspection/references/fsp-property-map.md"
    },
    {
      "id": "R-004",
      "observation": "仿真脚本默认 --out 落在 spec 同级，会写进只读 cases/；必须显式指定 _scratch/regress/",
      "evidence": "defects/D-002 根因与验证",
      "destination": "defects",
      "landed": true,
      "target_path": "defects/D-002-sweep-default-out-writes-into-readonly-cases.md"
    },
    {
      "id": "R-005",
      "observation": "把 .fsp 反解析成 manifest/spectra/diff/summary 四份 JSON 是可复用能力，应立项为独立技能而非一次性脚本",
      "evidence": "skills/INDEX.md stage 1.5 条目 + 双门禁 ALL GREEN",
      "destination": "scripts",
      "landed": true,
      "target_path": "skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py"
    },
    {
      "id": "R-006",
      "observation": "单次偏差解释（0.82 vs 0.97）只属于这个包，不进技能正文",
      "evidence": "notes/repro-2026-11-07-fsp-calibration.md §3 数值对照表",
      "destination": "notes",
      "landed": true,
      "target_path": "notes/repro-2026-11-07-fsp-calibration.md"
    },
    {
      "id": "R-007",
      "observation": "P01 包 488.8 MB（主 .fsp 347 MB）超过单文件 100 MB 入库上限，check_packages.py 目前不查体积",
      "evidence": "journal/2026-11-07.md 下次从这接 §3；属 C 档，待办",
      "destination": "defects",
      "landed": false,
      "target_path": null
    }
  ],
  "rerun_commands": [
    "python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config skills/fdtd-lumerical-fsp-introspection/assets/inspect_config.example.json --out _scratch/regress/fsp-20261107 --json",
    "python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec cases/P01_Absorber_042/config/spec_p01.json --out _scratch/regress/p01-20261107/baseline",
    "python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec _scratch/p01_probe/spec_fsp_calibrated.json --out _scratch/regress/p01-20261107/fsp_calibrated"
  ]
}
```
