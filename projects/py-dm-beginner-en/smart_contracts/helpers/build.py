import logging
import subprocess
from pathlib import Path
from shutil import rmtree

from smart_contracts.helpers.util import find_app_spec_file

logger = logging.getLogger(__name__)
deployment_extension = "py"


def build(output_dir: Path, contract_path: Path) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        rmtree(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    logger.info(f"Exporting {contract_path} to {output_dir}")

    build_result = subprocess.run(
        [
            "poetry",
            "run",
            "puyapy",
            contract_path.absolute(),
            f"--out-dir={output_dir}",
            "--output-arc32",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if build_result.returncode:
        raise Exception(f"Could not build contract:\n{build_result.stdout}")

    app_spec_file_name = find_app_spec_file(output_dir)
    if app_spec_file_name is None:
        raise Exception("Could not generate typed client, .arc32.json file not found")

    generate_result = subprocess.run(
        [
            "algokit",
            "generate",
            "client",
            output_dir / app_spec_file_name,
            "--output",
            output_dir / f"client.{deployment_extension}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if generate_result.returncode:
        if "No such command" in generate_result.stdout:
            raise Exception(
                "Could not generate typed client, requires AlgoKit 1.1 or "
                "later. Please update AlgoKit"
            )
        else:
            raise Exception(
                f"Could not generate typed client:\n{generate_result.stdout}"
            )
    return output_dir / app_spec_file_name
