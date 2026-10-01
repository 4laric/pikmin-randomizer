"""Render a local self-contained dashboard from the shared workflow registry."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow.registry import Registry
from workflow.controller import ram_percent
from workflow.dashboard import render_dashboard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    target = args.output or root / 'output/workflow/controller/throughput.html'
    if not target.resolve().is_relative_to(root / 'output'):
        parser.error('Dashboard must stay under workspace output/')
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(reg.throughput_status(ram_percent=ram_percent())), encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
