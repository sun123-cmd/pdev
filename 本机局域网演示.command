#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
python3 tools/demo.py start --local --access lan
result=$?
echo
if [ "$result" -eq 0 ]; then echo "操作完成，可关闭此窗口。"; else echo "未完成，请保留上方错误信息。"; fi
read -r -p "按回车关闭窗口…"
exit "$result"
