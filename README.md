# Distance Curve Tools

GROMACS 分子动力学**距离-时间曲线**后处理工具集：批量噪声增强 + PyQt5 交互式曲线编辑器。

## 功能概览

| 工具 | 类型 | 功能 |
|------|------|------|
| `augment_gui.py` | CLI | 按配置对距离曲线分段添加扰动，输出 CSV / XVG |
| `curve_editor.py` | GUI | 拖拽编辑曲线，支持撤销/重做，读写 XVG / CSV |
| `perlin_noise.py` | 模块 | 一维 Perlin 噪声生成 |

## 快速开始

```bash
git clone https://github.com/Ling-MD/distance-curve-tools.git
cd distance-curve-tools
pip install -r requirements.txt

# 运行示例
bash examples/run_example.sh
```

## 安装

```bash
pip install -r requirements.txt
```

依赖：`numpy`、`pandas`、`PyQt5`、`pyqtgraph`

## 使用说明

### 1. 批量曲线增强 (`augment_gui.py`)

从 GROMACS `gmx distance` 或自定义脚本获得距离 CSV 后：

```bash
python src/augment_gui.py \
  --input examples/sample_input.csv \
  --config examples/config.example.json \
  --output examples/augmented_output.csv
```

**输入 CSV 格式：**

```csv
Time_ns,Distance_A
0.0,12.5
10.0,12.8
...
```

**配置文件 (`config.example.json`)：**

```json
{
  "global_clip": [0, 30],
  "regions": [
    {"t0": 0, "t1": 150, "amp": 0.6, "pts": 5, "mode": "sin_noise"},
    {"t0": 150, "t1": 170, "amp": 2.2, "pts": 4, "mode": "gaussian"}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `global_clip` | 距离值裁剪区间 [min, max]（Å） |
| `regions[].t0/t1` | 时间段范围（ns） |
| `regions[].amp` | 扰动振幅 |
| `regions[].pts` | 段内插值点数 |
| `regions[].mode` | `sin` / `sin_noise` / `gaussian` / `perlin` / `spike` |

### 2. 交互式曲线编辑器 (`curve_editor.py`)

```bash
python src/curve_editor.py
```

- 菜单 **File → Open** 加载 `examples/sample_input.xvg` 或 CSV
- 拖拽数据点编辑曲线，邻近点通过高斯/余弦核变形
- **Ctrl+Z / Ctrl+Y** 撤销/重做
- 保存为 XVG 或 CSV

### 3. 从 GROMACS 获取距离数据

```bash
# 示例：计算两组原子质心距离
gmx distance -s md.tpr -f md.xtc -select 'com of group "Protein" plus com of group "Ligand"' -oall dist.xvg
```

将 XVG 转为 CSV 后，即可作为 `augment_gui.py` 的输入。

## 示例文件

| 文件 | 说明 |
|------|------|
| `examples/sample_input.csv` | 输入距离曲线（CSV，单位 Å） |
| `examples/sample_input.xvg` | 输入距离曲线（GROMACS XVG 格式，单位 nm） |
| `examples/config.example.json` | 扰动配置模板 |
| `examples/augmented_output.csv` | 增强后的输出示例 |
| `examples/augmented_output.xvg` | 增强后的 XVG 输出示例 |
| `examples/run_example.sh` | 一键运行示例脚本 |

## 项目结构

```
distance-curve-tools/
├── src/
│   ├── augment_gui.py      # 批量增强
│   ├── curve_editor.py     # GUI 编辑器
│   └── perlin_noise.py     # 噪声模块
├── examples/               # 示例数据与脚本
├── requirements.txt
└── README.md
```

## License

MIT
