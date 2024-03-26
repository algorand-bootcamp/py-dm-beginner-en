# py-dm-beginner-en

This project has been generated using AlgoKit. See below for default getting started instructions.

# Setup

### Pre-requisites

- [Python 3.12](https://www.python.org/downloads/) or later
- [Docker](https://www.docker.com/) (only required for LocalNet)

### Initial setup

1. Clone this repository locally
2. Install pre-requisites:
   - Make sure to have [Docker](https://www.docker.com/) installed and running on your machine.
   - Install `AlgoKit` - [Link](https://github.com/algorandfoundation/algokit-cli#install): The recommended version is `1.7.3`. Ensure you can execute `algokit --version` and get `1.7.1` or later.
   - Bootstrap your local environment; run `algokit bootstrap all` within this folder, which will:
     - Install `Poetry` - [Link](https://python-poetry.org/docs/#installation): The minimum required version is `^1.7`. Ensure you can execute `poetry -V` and get `1.2`+
     - Run `poetry install` in the root directory, which will set up a `.venv` folder with a Python virtual environment and also install all Python dependencies
     - Copy `.env.template` to `.env`
   - Run `algokit localnet start` to start a local Algorand network in Docker. If you are using VS Code launch configurations provided by the template, this will be done automatically for you.
3. Open the project and start debugging / developing via:
   - VS Code
     1. Open the repository root in VS Code
     2. Install recommended extensions
     3. Hit F5 (or whatever you have debug mapped to) and it should start running with breakpoint debugging.
        > **Note**
        > If using Windows: Before running for the first time you will need to select the Python Interpreter.
        1. Open the command palette (Ctrl/Cmd + Shift + P)
        2. Search for `Python: Select Interpreter`
        3. Select `./.venv/Scripts/python.exe`
   - JetBrains IDEs (please note, this setup is primarily optimized for PyCharm Community Edition)
     1. Open the repository root in the IDE
     2. It should automatically detect it's a Poetry project and set up a Python interpreter and virtual environment.
     3. Hit Shift+F10|Ctrl+R (or whatever you have debug mapped to) and it should start running with breakpoint debugging. Please note, JetBrains IDEs on Windows have a known bug that in some cases may prevent executing shell scripts as pre-launch tasks, for workarounds refer to [JetBrains forums](https://youtrack.jetbrains.com/issue/IDEA-277486/Shell-script-configuration-cannot-run-as-before-launch-task).
   - Other
     1. Open the repository root in your text editor of choice
     2. In a terminal run `poetry shell`
     3. Run `python -m smart_contracts` through your debugger of choice

### Subsequently

1. If you update to the latest source code and there are new dependencies you will need to run `algokit bootstrap all` again
2. Follow step 3 above

> For guidance on `smart_contracts` folder and adding new contracts to the project please see [README](smart_contracts/README.md) on the respective folder.### Continuous Integration / Continuous Deployment (CI/CD)

This project uses [GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions) to define CI/CD workflows, which are located in the [.github/workflows](`../../.github/workflows`) folder.

> Please note, if you instantiated the project with --workspace flag in `algokit init` it will automatically attempt to move the contents of the `.github` folder to the root of the workspace.

### Debugging Smart Contracts

This project is optimized to work with AlgoKit AVM Debugger extension. To activate it:
Refer to the commented header in the `__main__.py` file in the `smart_contracts` folder.

If you have opted in to include VSCode launch configurations in your project, you can also use the `Debug TEAL via AlgoKit AVM Debugger` launch configuration to interactively select an available trace file and launch the debug session for your smart contract.

For information on using and setting up the `AlgoKit AVM Debugger` VSCode extension refer [here](https://github.com/algorandfoundation/algokit-avm-vscode-debugger). To install the extension from the VSCode Marketplace, use the following link: [AlgoKit AVM Debugger extension](https://marketplace.visualstudio.com/items?itemName=algorandfoundation.algokit-avm-vscode-debugger).

#### Setting up GitHub for CI/CD workflow and TestNet deployment

  1. Every time you have a change to your smart contract, and when you first initialize the project you need to [build the contract](#initial-setup) and then commit the `smart_contracts/artifacts` folder so the [output stability](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/articles/output_stability.md) tests pass
  2. Decide what values you want to use for the `allow_update`, `allow_delete` and the `on_schema_break`, `on_update` parameters specified in [`contract.py`](./smart_contracts/digital_marketplace/contract.py).
     When deploying to LocalNet these values are both set to allow update and replacement of the app for convenience. But for non-LocalNet networks
     the defaults are more conservative.
     These default values will allow the smart contract to be deployed initially, but will not allow the app to be updated or deleted if is changed and the build will instead fail.
     To help you decide it may be helpful to read the [AlgoKit Utils app deployment documentation](https://github.com/algorandfoundation/algokit-utils-ts/blob/main/docs/capabilities/app-deploy.md) or the [AlgoKit smart contract deployment architecture](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/architecture-decisions/2023-01-12_smart-contract-deployment.md#upgradeable-and-deletable-contracts).
  3. Create a [Github Environment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#creating-an-environment) named `Test`.
     Note: If you have a private repository and don't have GitHub Enterprise then Environments won't work and you'll need to convert the GitHub Action to use a different approach. Ignore this step if you picked `Starter` preset.
  4. Create or obtain a mnemonic for an Algorand account for use on TestNet to deploy apps, referred to as the `DEPLOYER` account.
  5. Store the mnemonic as a [secret](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#environment-secrets) `DEPLOYER_MNEMONIC`
     in the Test environment created in step 3.
  6. The account used to deploy the smart contract will require enough funds to create the app, and also fund it. There are two approaches available here:
     * Either, ensure the account is funded outside of CI/CD.
       In Testnet, funds can be obtained by using the [Algorand TestNet dispenser](https://bank.testnet.algorand.network/) and we recommend provisioning 50 ALGOs.
     * Or, fund the account as part of the CI/CD process by using a `DISPENSER_MNEMONIC` GitHub Environment secret to point to a separate `DISPENSER` account that you maintain ALGOs in (similarly, you need to provision ALGOs into this account using the [TestNet dispenser](https://bank.testnet.algorand.network/)).

#### Continuous Integration

For pull requests and pushes to `main` branch against this repository the following checks are automatically performed by GitHub Actions:
 - Python dependencies are audited using [pip-audit](https://pypi.org/project/pip-audit/)
 - Code formatting is checked using [Black](https://github.com/psf/black)
 - Linting is checked using [Ruff](https://github.com/charliermarsh/ruff)
 - Types are checked using [mypy](https://mypy-lang.org/)
 - Python tests are executed using [pytest](https://docs.pytest.org/)
 - Smart contract artifacts are built
 - Smart contract artifacts are checked for [output stability](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/articles/output_stability.md)
 - Smart contract is deployed to a AlgoKit LocalNet instance

#### Continuous Deployment

For pushes to `main` branch, after the above checks pass, the following deployment actions are performed:
  - The smart contract(s) are deployed to TestNet using [AlgoNode](https://algonode.io).

> Please note deployment is also performed via `algokit deploy` command which can be invoked both via CI as seen on this project, or locally. For more information on how to use `algokit deploy` please see [AlgoKit documentation](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/features/deploy.md).

# Tools

This project makes use of Algorand Python to build Algorand smart contracts. The following tools are in use:

- [Algorand](https://www.algorand.com/) - Layer 1 Blockchain; [Developer portal](https://developer.algorand.org/), [Why Algorand?](https://developer.algorand.org/docs/get-started/basics/why_algorand/)
- [AlgoKit](https://github.com/algorandfoundation/algokit-cli) - One-stop shop tool for developers building on the Algorand network; [docs](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/algokit.md), [intro tutorial](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/tutorials/intro.md)
- [Algorand Python](https://github.com/algorandfoundation/puya) - A semantically and syntactically compatible, typed Python language that works with standard Python tooling and allows you to express smart contracts (apps) and smart signatures (logic signatures) for deployment on the Algorand Virtual Machine (AVM); [docs](https://github.com/algorandfoundation/puya), [examples](https://github.com/algorandfoundation/puya/tree/main/examples)
- [AlgoKit Utils](https://github.com/algorandfoundation/algokit-utils-py) - A set of core Algorand utilities that make it easier to build solutions on Algorand.
- [Poetry](https://python-poetry.org/): Python packaging and dependency management.- [Black](https://github.com/psf/black): A Python code formatter.- [Ruff](https://github.com/charliermarsh/ruff): An extremely fast Python linter.

- [mypy](https://mypy-lang.org/): Static type checker.
- [pytest](https://docs.pytest.org/): Automated testing.
- [pip-audit](https://pypi.org/project/pip-audit/): Tool for scanning Python environments for packages with known vulnerabilities.
 - [pre-commit](https://pre-commit.com/): A framework for managing and maintaining multi-language pre-commit hooks, to enable pre-commit you need to run `pre-commit install` in the root of the repository. This will install the pre-commit hooks and run them against modified files when committing. If any of the hooks fail, the commit will be aborted. To run the hooks on all files, use `pre-commit run --all-files`.
It has also been configured to have a productive dev experience out of the box in [VS Code](https://code.visualstudio.com/), see the [.vscode](./.vscode) folder.

