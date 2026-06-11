# Mac Anaconda 제거 및 Python 환경 재정리 가이드

이 문서는 현재 맥과 동일하게 마이그레이션된 다른 Mac에서 Anaconda 설정을 걷어내고, 프로젝트별 `.venv` + `pyenv` 중심으로 Python 환경을 최소화하기 위한 참고 절차입니다.

## 목표

- 전역 `(base)` conda 자동 진입 제거
- 쉘 설정 파일에서 Anaconda 초기화 블록 제거
- `/opt/anaconda3` 또는 사용자 홈의 Anaconda 설치물 제거
- 프로젝트는 `.python-version`과 `.venv`로 독립 실행

## 사전 확인

```bash
which conda
conda info --base
which python
python --version
pyenv versions
```

`conda info --base` 결과가 `/opt/anaconda3`이면 시스템 공용 위치에 설치된 상태입니다. `~/anaconda3` 또는 `~/miniconda3`이면 사용자 홈에 설치된 상태입니다.

## 쉘 설정 백업

```bash
mkdir -p ~/.shell_config_backups
cp ~/.zshrc ~/.shell_config_backups/.zshrc.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
cp ~/.zprofile ~/.shell_config_backups/.zprofile.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
cp ~/.bash_profile ~/.shell_config_backups/.bash_profile.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
cp ~/.bashrc ~/.shell_config_backups/.bashrc.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
```

## Anaconda 초기화 블록 제거

아래 파일을 열어 `# >>> conda initialize >>>`부터 `# <<< conda initialize <<<`까지의 블록을 제거합니다.

```bash
open -e ~/.zshrc
open -e ~/.zprofile
open -e ~/.bash_profile
open -e ~/.bashrc
```

수동 편집 후 새 터미널을 열어 `(base)`가 사라졌는지 확인합니다.

## Anaconda 설치물 제거

설치 경로를 확인한 뒤 해당 경로만 삭제합니다.

```bash
conda info --base
```

예시:

```bash
sudo rm -rf /opt/anaconda3
rm -rf ~/anaconda3
rm -rf ~/miniconda3
```

삭제 후 빈 디렉터리만 남았다면 다음처럼 제거합니다.

```bash
sudo rmdir /opt/anaconda3
```

## pyenv 기준 Python 확인

```bash
pyenv versions
pyenv global 3.12.10
python --version
```

`python: command not found`가 나오면 프로젝트 루트에 `.python-version`을 두거나, 전역 버전을 설정합니다.

```bash
# 프로젝트 루트에서 실행
echo "3.12.10" > .python-version
python --version
```

## 프로젝트 가상환경 재생성

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
```

## Codex에게 줄 수 있는 프롬프트

다른 맥에서 그대로 작업을 맡길 때는 아래 프롬프트를 사용합니다.

```text
현재 Mac은 이전 Mac을 마이그레이션해서 Anaconda/conda 설정이 남아 있습니다.
전역 conda base 자동 진입을 제거하고, Anaconda 설치물을 정리한 뒤,
이 프로젝트는 pyenv Python 3.12.10 + 프로젝트별 .venv 방식으로 다시 구성해 주세요.

요구사항:
- 삭제 전에 ~/.zshrc, ~/.zprofile, ~/.bash_profile, ~/.bashrc를 백업
- conda initialize 블록 제거
- conda info --base로 실제 Anaconda 설치 경로 확인
- /opt/anaconda3, ~/anaconda3, ~/miniconda3 중 실제 설치된 경로만 제거
- 프로젝트 루트에 .python-version이 없으면 3.12.10으로 생성
- .venv를 재생성하고 requirements.txt 설치
- pytest로 정상 동작 확인
- .venv, .env, 캐시, Chroma 로컬 DB는 커밋하지 않기
```
