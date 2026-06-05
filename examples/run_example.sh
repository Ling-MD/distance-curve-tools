#!/bin/bash
# 距离曲线增强示例
# 用法: bash examples/run_example.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 运行 augment_gui.py 示例 ==="
python3 src/augment_gui.py \
  --input examples/sample_input.csv \
  --config examples/config.example.json \
  --output examples/augmented_output.csv

echo ""
echo "输出文件:"
echo "  - examples/augmented_output.csv"
echo "  - examples/augmented_output.xvg"
echo ""
echo "=== 交互式编辑器 ==="
echo "运行: python3 src/curve_editor.py"
echo "在 GUI 中打开 examples/sample_input.xvg 或 examples/augmented_output.xvg 进行编辑"
