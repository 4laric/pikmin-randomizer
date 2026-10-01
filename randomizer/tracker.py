"""Read-only game-linked check tracker. Never exposes unchecked rewards."""
from collections import Counter
import tkinter as tk
from tkinter import ttk
from .catalog import (ITEM_IDS, REPAIR, color_inventory, field_capacity,
                      can_reach_manifest, check_area, bestiary_sources, START_AREAS)
from .seed import fingerprint, solo_rewards
from .stats import profile_lines
from .benefits import benefit_lines


class TrackerModel:
    def __init__(self, manifest):
        self.manifest = manifest
        self.fingerprint = fingerprint(manifest)
        self.rewards = solo_rewards(manifest) if manifest['mode'] == 'solo' else None
        self.item_names = {v: k for k, v in ITEM_IDS.items()}
        self.areas = {sid: area for sid, area, _ in START_AREAS.values()}

    def snapshot(self, data):
        if data['fingerprint'] != self.fingerprint:
            raise ValueError('Tracker session mismatch')
        checked = set(data['checked'])
        inventory = Counter(self.rewards[n] for n in checked) if self.rewards is not None else Counter(self.item_names[i] for i in data['received'])
        rows = []
        for name in self.manifest['locations']:
            sources = bestiary_sources(name, self.manifest)
            if sources:
                stages = {}
                for source in sources:
                    stage = source['stage']
                    stages[stage] = min(stages.get(stage, 999), source['first_day'])
                areas = tuple(self.areas[stage] for stage in sorted(stages))
                source_text = ', '.join(self.areas[stage] + (f' (day {day}+)' if day > 2 else '') for stage, day in sorted(stages.items()))
            else:
                areas = (check_area(name),)
                source_text = areas[0]
            status = 'Checked' if name in checked else 'Available' if can_reach_manifest(name, inventory, self.manifest) else 'Needs progression'
            rows.append(dict(name=name, status=status, areas=areas, source=source_text))
        cap = field_capacity(inventory, self.manifest['schema'] >= 2, self.manifest.get('starting_flarlic', 2))
        owned = color_inventory(inventory, self.manifest)
        onions = '   '.join(f'{color}: {"unlocked" if owned.get(color + " Onion", 0) else "locked"}' for color in ('Red', 'Yellow', 'Blue'))
        finale = ""
        if self.manifest.get("goal_mode") == "emperor_bulblax":
            finale = "    Emperor: " + ("defeated" if data.get("emperor_defeated") else "unlocked" if inventory[REPAIR] >= 25 else "locked until 25 repairs")
        from .session import death_link_summary
        death_link = death_link_summary(self.manifest, data)
        return dict(rows=rows, inventory=inventory, profiles=profile_lines(self.manifest, inventory),
                    benefits=benefit_lines(self.manifest, inventory) + ([death_link] if death_link else []), onions=onions,
                    summary=f'{len(checked)}/{len(rows)} checks    Repairs {inventory[REPAIR]}/{self.manifest["goal"]} required    Field cap {cap}{finale}')

    @staticmethod
    def filter_rows(rows, query='', area='All areas', status='Unchecked'):
        query = query.casefold().strip()
        return [r for r in rows if (not query or query in (r['name'] + ' ' + r['source']).casefold())
                and (area == 'All areas' or area in r['areas'])
                and (status == 'All checks' or status == 'Unchecked' and r['status'] != 'Checked' or r['status'] == status)]


class TrackerWindow:
    def __init__(self, root, manifest, on_close):
        self.model = TrackerModel(manifest)
        self.on_close = on_close
        self.data = None
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.title('Pikipelago — Tracker')
        self.window.geometry('940x620')
        self.window.minsize(660, 430)
        self.window.protocol('WM_DELETE_WINDOW', on_close)
        self.window.bind('<Escape>', lambda event: on_close())
        # F8 is handled by the same polling edge as the game to avoid double toggles.
        self.summary = tk.StringVar()
        self.details = tk.StringVar()
        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, textvariable=self.summary, font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='F8 / Esc: back to game. Game continues running — pause it first when needed.').pack(anchor='w', pady=(4, 8))
        ttk.Label(frame, textvariable=self.details).pack(anchor='w', pady=(0, 8))
        tabs = ttk.Notebook(frame)
        tabs.pack(fill='both', expand=True)
        checks = ttk.Frame(tabs, padding=8)
        items = ttk.Frame(tabs, padding=8)
        tabs.add(checks, text='Checks')
        tabs.add(items, text='Received items')
        filters = ttk.Frame(checks)
        filters.pack(fill='x', pady=(0, 8))
        self.query = tk.StringVar()
        self.area = tk.StringVar(value='All areas')
        self.status = tk.StringVar(value='Unchecked')
        ttk.Label(filters, text='Search').pack(side='left')
        self.search = ttk.Entry(filters, textvariable=self.query, width=24)
        self.search.pack(side='left', padx=6, fill='x', expand=True)
        ttk.Combobox(filters, textvariable=self.area, state='readonly', width=23,
                     values=['All areas'] + list(self.model.areas.values())).pack(side='left', padx=4)
        ttk.Combobox(filters, textvariable=self.status, state='readonly', width=18,
                     values=['Unchecked', 'Available', 'Needs progression', 'Checked', 'All checks']).pack(side='left')
        self.checks = self.tree(checks, ('status', 'name', 'source'), ('Status', 'Check', 'Area / source'), (130, 360, 300))
        self.checks.tag_configure('Checked', foreground='#65736b')
        self.checks.tag_configure('Available', foreground='#146638')
        self.checks.tag_configure('Needs progression', foreground='#875b19')
        self.items = self.tree(items, ('name', 'count'), ('Received item', 'Count'), (640, 80))
        self.count = tk.StringVar()
        ttk.Label(checks, textvariable=self.count).pack(anchor='w', pady=(6, 0))
        ttk.Label(frame, text='Available = reachable in seed logic, not a live proximity check. Bestiary sources include scheduled days.').pack(anchor='w', pady=(8, 0))
        for variable in (self.query, self.area, self.status): variable.trace_add('write', self.render_checks)

    @staticmethod
    def tree(parent, columns, labels, widths):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode='browse')
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        horizontal.pack(side='bottom', fill='x')
        scroll.pack(side='right', fill='y')
        tree.pack(side='left', fill='both', expand=True)
        for col, label, width in zip(columns, labels, widths):
            tree.heading(col, text=label)
            tree.column(col, width=width, minwidth=60)
        return tree

    def update(self, data):
        self.data = self.model.snapshot(data)
        self.summary.set(self.data['summary'])
        self.details.set('\n'.join([self.data['onions']] + self.data['profiles'] + self.data['benefits']))
        self.items.delete(*self.items.get_children())
        for name, count in sorted(self.data['inventory'].items()):
            self.items.insert('', 'end', values=(name, count))
        self.render_checks()

    def render_checks(self, *args):
        if self.data is None: return
        rows = self.model.filter_rows(self.data['rows'], self.query.get(), self.area.get(), self.status.get())
        self.checks.delete(*self.checks.get_children())
        for r in rows: self.checks.insert('', 'end', values=(r['status'], r['name'], r['source']), tags=(r['status'],))
        self.count.set(f'{len(rows)} matching checks')

    def show(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.search.focus_set()

    def hide(self):
        self.window.withdraw()
