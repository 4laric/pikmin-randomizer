import argparse
import json
from pathlib import Path
from .seed import generate, validate, fingerprint, solo_rewards, spheres
from .runner import launch
from .session import Session, SessionLock
from .catalog import field_capacity, can_reach_manifest, POPULATION, BESTIARY, ALL_EXPLORATION, NAMES, POSITRON


def main():
    parser = argparse.ArgumentParser(description="Pikmin Randomizer: standalone identity-placement milestone")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--seed", required=True)
    gen.add_argument("--campaign-enemies", action="store_true", help="Campaign-wide compatible pools, including Teki minibosses; overrides older enemy toggles")
    gen.add_argument("--starting-flarlic", type=int, choices=range(1, 11), default=1, help="Initial field capacity in tens (default 1 = 10 Pikmin)")
    gen.add_argument("--permanent-checks", action="store_true", help="Add 51 permanent obstacle completion checks")
    gen.add_argument("--progressive-color-stats", action="store_true", help="36 AP stat upgrades across three colors; enables permanent checks")
    gen.add_argument("--randomize-color-stats", action="store_true", help="Seeded damage, movement, attack rate and carrying strength per color")
    gen.add_argument("--expanded", action="store_true", help="Flarlic, population, bestiary and exploration checks")
    gen.add_argument('--starting-area', choices=['forest', 'navel', 'impact', 'spring', 'trial', 'random'], default='forest', help='Random includes four areas; excludes Final Trial')
    gen.add_argument('--all-areas', action='store_true', help='Enable five-area catalog with a fixed start')
    gen.add_argument('--miniboss-enemies', action='store_true', help='Experimental: three adult slots become Puffstool, Mamuta and Cannon Beetle')
    gen.add_argument('--per-spawn-enemies', action='store_true', help='Opt-in named adult Bulborb/Bulbear slots; overrides global family swaps')
    gen.add_argument('--group-spawn-enemies', action='store_true', help='Experimental dwarf/Sheargrub groups; implies per-spawn adults')
    gen.add_argument('--enemy-shuffle', action='store_true', help='Seeded compatible enemy-family swaps')
    gen.add_argument('--collection-checks', action='store_true', default=True, help='Onion corpse deliveries and population 10/25/50/100 per color')
    gen.add_argument('--starting-color', choices=['red', 'yellow', 'blue', 'random'], default='red', help='Non-default enables expanded checks')
    gen.add_argument("--slot", default="Player1")
    gen.add_argument("--mode", choices=["solo", "ap"], default="solo")
    gen.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("manifest", type=Path)
    run = sub.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--session-dir", type=Path, required=True)
    run.add_argument("--exe", type=Path)
    run.add_argument("--assets", type=Path)
    run.add_argument("--server")
    status = sub.add_parser("status", help="Show collected checks and the bestiary")
    status.add_argument("manifest", type=Path)
    status.add_argument("--session-dir", type=Path, required=True)
    status.add_argument("--output", type=Path)
    enemy_spoiler = sub.add_parser('enemy-spoiler', help='Explicit spoiler: named per-spawn enemy choices and source schedules')
    enemy_spoiler.add_argument('manifest', type=Path)
    enemy_spoiler.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        manifest = generate(args.seed, args.mode, args.slot, expanded=args.expanded, starting_area=args.starting_area, starting_color=args.starting_color, all_areas=args.all_areas, enemy_shuffle=args.enemy_shuffle, collection_checks=args.collection_checks, starting_flarlic=args.starting_flarlic, randomize_color_stats=args.randomize_color_stats, progressive_color_stats=args.progressive_color_stats, permanent_checks=args.permanent_checks, per_spawn_enemies=args.per_spawn_enemies, group_spawn_enemies=args.group_spawn_enemies, miniboss_enemies=args.miniboss_enemies, campaign_enemies=args.campaign_enemies)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as f:
            f.write(json.dumps(manifest, indent=2) + "\n")
        print(f"Created {args.output}: {len(manifest['locations'])} checks; start {manifest['profile']} / {manifest.get('starting_color', 'red')}; goal 25 repairs; physical placements pinned")
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate(manifest)
        if args.command == 'enemy-spoiler':
            from .enemy_slots import spoiler
            text = json.dumps(spoiler(manifest), indent=2) + '\n'
            if args.output: args.output.write_text(text, encoding='utf-8')
            else: print(text, end='')
        elif args.command == "validate":
            print(f"Valid {fingerprint(manifest)}; {len(manifest['locations'])} checks, {len(manifest['assignments'])} pinned parts")
            if manifest["mode"] == "solo":
                print(f"Conservative logic: {len(spheres(solo_rewards(manifest), manifest))} progression spheres")
        elif args.command == "status":
            with SessionLock(args.session_dir):
                session = Session(manifest, args.session_dir)
                checked = set(session.data["checked"])
                lines = ["# Pikmin Randomizer status", "",
                         f"Collected: {len(checked)}/{len(session.names)} checks. "
                         f"Field capacity: {field_capacity(session.inventory, manifest['schema'] >= 2, manifest.get('starting_flarlic', 2))}. "
                         f"Repair goal: {min(session.inventory['Ship Repair'], 25)}/25.", "",
                         "Population entries record reached milestones, not the current population.", ""]
                from .benefits import benefit_lines
                lines += benefit_lines(manifest, session.inventory) + [""]
                from .stats import profile_lines
                if "color_stats" in manifest or manifest.get("progressive_color_stats"):
                    lines += ["## Color profiles", ""] + profile_lines(manifest, session.inventory) + [""]
                from .catalog import population_checks, TOTAL_POPULATION, DELIVERY_BESTIARY, FINE_POPULATION, OBSTACLES, NEW_BESTIARY, bestiary_sources, START_AREAS
                for category, entries in (("Parts and Onions", NAMES + (POSITRON,)), ("Population", population_checks(manifest) if manifest['schema'] >= 7 else POPULATION),
                                          ("Bestiary - deliveries and defeats" if manifest['schema'] >= 7 else "Bestiary - first defeats", ({**DELIVERY_BESTIARY, **NEW_BESTIARY}) if manifest['schema'] >= 7 else BESTIARY), ("Exploration", ALL_EXPLORATION), ("Permanent obstacles", OBSTACLES)):
                    enabled = [n for n in entries if n in session.names]
                    if not enabled: continue
                    lines += ["## " + category, ""]
                    for name in enabled:
                        available = can_reach_manifest(name, session.inventory, manifest)
                        suffix = "" if name in checked else (" - available in logic" if available else " - needs progression")
                        sources = bestiary_sources(name, manifest)
                        if sources:
                            stages = {}
                            for row in sources: stages[row['stage']] = min(stages.get(row['stage'], 999), row['first_day'])
                            descriptions = [next(area for sid, area, _ in START_AREAS.values() if sid == stage)
                                + (f" (day {day}+)" if day > 2 else '') for stage, day in sorted(stages.items())]
                            suffix += ' — sources: ' + ', '.join(descriptions)
                        lines.append(f"- [{'x' if name in checked else ' '}] {name}{suffix}")
                    lines.append("")
                text = "\n".join(lines)
                if args.output:
                    args.output.write_text(text, encoding="utf-8")
                else:
                    print(text)
        else:
            launch(manifest, args.session_dir.resolve(), args.exe, args.assets, args.server)


if __name__ == "__main__":
    main()
