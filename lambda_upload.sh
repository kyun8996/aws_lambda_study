# lambda 함수에는 request 패키지가 설치되어 있는 환경이 아니어서 패키지를 업로드 해야한다.

# 로컬에 작업용 폴더 만들기
mkdir lambda_deploy
cd lambda_deploy

# 로컬에 pip 설치 경로 지정하여 설치
# requests 패키지를 현재 디렉터리에 직접 설치하라는 명령어
pip install requests -t .

# ZIP 파일로 압축
python -m zipfile -c ..\lambda_deploy.zip .

# ZIP 파일 업로드 
## Lambda 함수 → “코드” 탭 → “에서 업로드” 선택
## “.zip 파일 업로드” 클릭 후 lambda_deploy.zip 선택