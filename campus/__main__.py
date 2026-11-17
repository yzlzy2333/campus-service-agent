
"""中文命令行入口。"""
import argparse
import json
import re
from pathlib import Path

from .knowledge import Knowledge
from .service import Offline, Session


def print_guides(kb):
    print(f"支持的校园事务（{len(kb.catalog)} 项模拟指南）")
    for guide in kb.catalog.values():
        print(f"- {guide.name}")


def main():
    parser = argparse.ArgumentParser(description="校园办事指南（模拟资料）")
    parser.add_argument("--offline", action="store_true", help="使用本地规则演示，无网络请求")
    parser.add_argument("--mode", choices=["rag", "full"], default="rag")
    parser.add_argument("--rebuild-index", action="store_true", help="重新加载指南并核验索引后退出")
    parser.add_argument("--list-guides", action="store_true", help="列出当前支持的模拟办事事项")
    parser.add_argument("--log", type=Path, help="将每轮脱敏记录追加到 JSONL 文件")
    args = parser.parse_args()
    kb = Knowledge()
    if args.list_guides:
        print_guides(kb)
        return 0
    if args.rebuild_index:
        print(f"内存索引重建完成：{len(kb.catalog)} 项事务，{len(kb.passages)} 个片段。")
        if kb.errors:
            print("无效资料：", kb.errors)
            return 1
        return 0
    if args.offline:
        engine = Offline(kb, args.mode)
    else:
        from .live import Live
        try:
            engine = Live(kb, args.mode)
        except ValueError as exc:
            print(exc)
            return 2
    mode = "本地规则演示" if args.offline else f"DeepSeek API · {engine.model_name}"
    print(f"校园办事指南｜模拟资料｜{mode}｜{args.mode}")
    print("输入 /list 查看支持事项，/new 开始新会话，/exit 退出。")
    session = Session()
    while True:
        try:
            message = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message == "/exit":
            break
        if message == "/list":
            print_guides(kb)
        elif message == "/new":
            session = Session()
            print("已开始新会话。")
        elif message:
            turn = engine.ask(message, session)
            answer = turn.answer.rsplit("\n来源（模拟资料）\n", 1)[0] if turn.citations else turn.answer
            answer = re.sub(r"[ \t]*\[[0-9]+\]", "", answer)
            print("\n助手 > " + answer)
            if args.log:
                with args.log.open("a", encoding="utf-8") as log:
                    log.write(json.dumps(turn.record(), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
