import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return (p.stdout or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="")
    parser.add_argument("--date", default="", help="YYYYMMDD; empty means latest trading day")
    parser.add_argument("--universe", default="B", choices=["A", "B"])
    parser.add_argument("--out-md", default="", help="Optional output markdown path")
    parser.add_argument("--email-to", default="")
    parser.add_argument("--email-config", default="")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    module_root = Path(__file__).resolve().parents[2]
    base_dir = Path(args.base_dir).resolve() if args.base_dir else module_root
    data_root = base_dir / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    fetch_script = module_root / "src" / "fetch" / "fetch_review_data.py"
    plot_script = module_root / "src" / "plot" / "plot_attack_sequence.py"
    enrich_script = module_root / "src" / "enrich" / "professionalize_recap.py"
    pdf_script = module_root / "src" / "report" / "generate_recap_pdf.py"
    md_script = module_root / "src" / "report" / "generate_recap_md.py"
    mail_script = module_root / "src" / "notify" / "send_email_report.py"

    date_arg = (args.date or "").strip()
    out_dir = run(
        [
            sys.executable,
            str(fetch_script),
            "--base-dir",
            str(data_root),
            "--universe",
            args.universe,
        ]
        + (["--date", date_arg] if date_arg else []),
        cwd=module_root,
    )
    data_dir = Path(out_dir).resolve()

    run(
        [sys.executable, str(plot_script), "--data-dir", str(data_dir), "--mode", "chain", "--top", "8", "--out", "attack_sequence_chain.png"],
        cwd=module_root,
    )

    run([sys.executable, str(enrich_script), "--data-dir", str(data_dir)], cwd=module_root)

    day = date_arg if (len(date_arg) == 8 and date_arg.isdigit()) else data_dir.name
    if len(day) == 8 and day.isdigit():
        pdf_name = f"{day[0:4]}年{day[4:6]}月{day[6:8]}日复盘.pdf"
    else:
        pdf_name = f"{day}复盘.pdf"
    pdf_dir = module_root / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_out = pdf_dir / pdf_name

    pdf_path = run([sys.executable, str(pdf_script), "--data-dir", str(data_dir), "--out", str(pdf_out)], cwd=module_root)

    # Markdown report (preferred)
    md_dir = module_root / "md"
    md_dir.mkdir(parents=True, exist_ok=True)
    md_name = pdf_name.replace(".pdf", ".md")
    md_out = Path(args.out_md).resolve() if args.out_md else (md_dir / md_name)
    md_path = run([sys.executable, str(md_script), "--data-dir", str(data_dir), "--out", str(md_out)], cwd=module_root)

    if args.send:
        if not args.email_to:
            raise RuntimeError("--send requires --email-to")

        config_path = Path(args.email_config).resolve() if args.email_config else (module_root / "email_config.json")
        mail_cmd = [
            sys.executable,
            str(mail_script),
            "--to",
            args.email_to,
            "--pdf",
            str(Path(pdf_path).resolve()),
            "--subject",
            f"A股复盘 {data_dir.name}",
            "--body",
            "请查收复盘PDF。",
        ]
        if config_path.exists():
            mail_cmd += ["--config", str(config_path)]
        run(
            mail_cmd,
            cwd=module_root,
        )

    print(str(pdf_path))


if __name__ == "__main__":
    main()
