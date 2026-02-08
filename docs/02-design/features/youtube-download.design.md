# Design: youtube-download

> Feature: YouTube 영상 실제 다운로드 및 파일 업로드 저장 구현
> Plan: `docs/01-plan/features/youtube-download.plan.md`
> Created: 2026-02-08

## 1. 구현 순서

```
1. [BE] requirements.txt - yt-dlp 의존성 추가
2. [BE] video_processor.py - YouTube 다운로드 + 파일 저장 로직
3. [BE] video_processor.py - 파일 업로드 디스크 저장 로직
```

프론트엔드 변경 없음. 백엔드 2개 파일만 수정.

## 2. Backend 설계

### 2.1 의존성 추가

**파일**: `backend/requirements.txt`

```
yt-dlp>=2024.0.0
```

### 2.2 VideoProcessor 재설계

**파일**: `backend/src/services/video_processor.py`

#### 2.2.1 yt-dlp 가용성 체크

```python
def _check_ytdlp(self) -> bool:
    """yt-dlp 설치 여부 확인"""
    try:
        import yt_dlp
        return True
    except ImportError:
        return False
```

#### 2.2.2 process_youtube() 변경

**현재 (Mock)**:
```
sleep(1) → _simulate_analysis()
```

**변경 후**:
```
1. yt-dlp 설치 여부 확인 → 미설치 시 ERROR
2. yt-dlp extract_info로 메타정보 추출 (제목, duration)
3. video.title, video.duration DB 업데이트
4. yt-dlp로 영상 다운로드 → uploads/{video_id}.mp4
5. 다운로드 진행률 → progress_hooks로 DB 업데이트 (10~80%)
6. _simulate_analysis() 호출 (하이라이트 분석은 여전히 Mock)
```

**상세 설계**:

```python
async def process_youtube(self, video_id: str, url: str):
    try:
        # Step 1: yt-dlp 확인
        if not self._check_ytdlp():
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(
                    video_id, ProcessingStatus.ERROR, 0,
                    "yt-dlp가 설치되지 않았습니다. pip install yt-dlp"
                )
                await db.commit()
            return

        import yt_dlp

        # Step 2: 메타정보 추출 (동기 → asyncio.to_thread)
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            await repo.update_status(
                video_id, ProcessingStatus.PROCESSING, 5,
                "YouTube 영상 정보 가져오는 중..."
            )
            await db.commit()

        info = await asyncio.to_thread(self._extract_youtube_info, url)

        # Step 3: 메타정보 DB 반영
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            video = await repo.get_by_id(video_id)
            if video:
                video.title = info.get("title", video.title)
                video.duration = info.get("duration")
                video.updated_at = datetime.now()
                await db.flush()
            await repo.update_status(
                video_id, ProcessingStatus.PROCESSING, 10,
                "영상 다운로드 중..."
            )
            await db.commit()

        # Step 4: 영상 다운로드
        output_path = str(Path(get_settings().upload_dir) / f"{video_id}.mp4")
        await asyncio.to_thread(
            self._download_youtube, url, output_path, video_id
        )

        # Step 5: 다운로드 완료 확인
        if not os.path.exists(output_path):
            raise FileNotFoundError("YouTube 영상 다운로드에 실패했습니다")

        # Step 6: Mock 분석 (기존 유지)
        await self._simulate_analysis(video_id)

    except Exception as e:
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
            await db.commit()
```

#### 2.2.3 YouTube 헬퍼 메서드

```python
def _extract_youtube_info(self, url: str) -> dict:
    """YouTube 메타정보 추출 (동기)"""
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", ""),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
        }


def _download_youtube(self, url: str, output_path: str, video_id: str):
    """YouTube 영상 다운로드 (동기, asyncio.to_thread로 호출)"""
    import yt_dlp

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [
            lambda d: self._on_download_progress(d, video_id)
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
```

#### 2.2.4 다운로드 진행률 콜백

```python
def _on_download_progress(self, d: dict, video_id: str):
    """yt-dlp 다운로드 진행률 콜백 (동기 컨텍스트에서 실행)"""
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        downloaded = d.get("downloaded_bytes", 0)
        if total > 0:
            percent = int((downloaded / total) * 70) + 10  # 10~80 범위
            # 동기 컨텍스트이므로 별도 이벤트 루프에서 DB 업데이트
            # 빈번한 호출 방지를 위해 5% 단위로만 업데이트
            if percent % 5 == 0:
                self._sync_update_progress(video_id, percent, "영상 다운로드 중...")
```

**진행률 동기 업데이트 방식**:
- yt-dlp progress_hooks는 동기 콜백
- `asyncio.to_thread()` 내부에서 실행되므로 async 사용 불가
- 별도 동기 DB 세션 생성하거나, 진행률을 인메모리에 저장 후 별도 업데이트
- **간단한 구현**: 인메모리 progress dict 사용, 폴링 시 반영

```python
# 클래스 멤버
_download_progress: dict[str, int] = {}

def _on_download_progress(self, d: dict, video_id: str):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        downloaded = d.get("downloaded_bytes", 0)
        if total > 0:
            self._download_progress[video_id] = int((downloaded / total) * 70) + 10
```

다운로드 완료 후 `_download_progress`에서 제거하고 DB 일괄 업데이트.

#### 2.2.5 process_file() 변경

**현재 (Mock)**:
```
sleep(0.3) 반복 → _simulate_analysis()
```

**변경 후**:
```
1. uploads 디렉토리 확인/생성
2. 파일을 uploads/{video_id}_{original_filename}으로 저장
3. video.source_filename에 저장된 파일명 기록
4. _simulate_analysis() 호출 (Mock 유지)
```

**상세 설계**:

```python
async def process_file(self, video_id: str, file):
    try:
        upload_dir = Path(get_settings().upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: 파일 저장
        safe_filename = f"{video_id}_{file.filename}"
        file_path = upload_dir / safe_filename

        async with async_session_maker() as db:
            repo = VideoRepository(db)
            await repo.update_status(
                video_id, ProcessingStatus.UPLOADING, 10,
                "영상 저장 중..."
            )
            await db.commit()

        # 파일 디스크 저장
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Step 2: source_filename 업데이트
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            video = await repo.get_by_id(video_id)
            if video:
                video.source_filename = safe_filename
                video.updated_at = datetime.now()
                await db.flush()
            await repo.update_status(
                video_id, ProcessingStatus.PROCESSING, 30,
                "분석 준비 중..."
            )
            await db.commit()

        # Step 3: Mock 분석
        await self._simulate_analysis(video_id)

    except Exception as e:
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
            await db.commit()
```

### 2.3 Export 연동 확인

**파일**: `backend/src/api/highlights.py` (변경 없음)

현재 Export 엔드포인트의 video_path 결정 로직:
```python
if video.source_type == "file" and video.source_filename:
    video_path = str(Path(get_settings().upload_dir) / video.source_filename)
elif video.source_type == "youtube" and video.source_url:
    video_path = str(Path(get_settings().upload_dir) / f"{video.id}.mp4")
```

- YouTube: `uploads/{video_id}.mp4` → `_download_youtube`의 output_path와 일치 ✅
- File: `uploads/{source_filename}` → `process_file`의 safe_filename과 일치 ✅

## 3. 시퀀스 다이어그램

### YouTube 흐름

```
User        Frontend         Backend              yt-dlp         Disk
 |              |                |                    |             |
 |--[YT URL]--->|                |                    |             |
 |              |--POST /youtube->|                    |             |
 |              |<--{video_id}---|                    |             |
 |              |                |--extract_info----->|             |
 |              |                |<--{title,duration}-|             |
 |              |--GET /video--->|                    |             |
 |              |<--{progress:5}-|                    |             |
 |              |                |--download--------->|             |
 |              |                |                    |--save------>|
 |              |                |<--progress_hooks---|   .mp4      |
 |              |--GET /video--->|                    |             |
 |              |<-{progress:50}-|                    |             |
 |              |                |                    |             |
 |              |                |--mock_analysis-----|             |
 |              |                |---INSERT highlights--|           |
 |              |--GET /video--->|                    |             |
 |              |<-{completed}---|                    |             |
 |              |                |                    |             |
 |--[Export]--->|--POST /export->|                    |             |
 |              |                |--FFmpeg clip--------|----------->|
 |              |--GET /download->|<--------------------|-----------|
 |<-[mp4 file]--|                |                    |             |
```

### 파일 업로드 흐름

```
User        Frontend         Backend              Disk
 |              |                |                   |
 |--[File]----->|                |                   |
 |              |--POST /upload->|                   |
 |              |                |--file.read()      |
 |              |                |--write----------->|
 |              |                |   {id}_{name}.mp4 |
 |              |<--{video_id}---|                   |
 |              |                |                   |
 |              |                |--mock_analysis     |
 |              |--GET /video--->|                   |
 |              |<-{completed}---|                   |
 |              |                |                   |
 |--[Export]--->|--POST /export->|                   |
 |              |                |--FFmpeg clip------>|
 |              |--GET /download->|                  |
 |<-[mp4 file]--|                |                   |
```

## 4. 에러 처리

| 상황 | 에러 메시지 | status |
|------|-----------|--------|
| yt-dlp 미설치 | "yt-dlp가 설치되지 않았습니다. pip install yt-dlp" | ERROR |
| YouTube URL 접근 불가 | yt-dlp 에러 메시지 전달 | ERROR |
| 영상 다운로드 실패 | "YouTube 영상 다운로드에 실패했습니다" | ERROR |
| 디스크 저장 실패 | Exception 메시지 | ERROR |
| 파일 읽기 실패 | Exception 메시지 | ERROR |

## 5. 검증 항목

| ID | 검증 항목 | 방법 |
|----|----------|------|
| V-1 | YouTube URL 입력 → 실제 mp4 파일이 uploads/ 에 저장되는지 | ls uploads/ 확인 |
| V-2 | video.title이 YouTube 제목으로 업데이트되는지 | GET /api/videos/{id} 응답 확인 |
| V-3 | video.duration이 실제 값으로 저장되는지 | GET /api/videos/{id} 응답 확인 |
| V-4 | 파일 업로드 → uploads/{video_id}_{filename}으로 저장되는지 | ls uploads/ 확인 |
| V-5 | 저장된 영상 → Export → Download 전체 흐름 동작하는지 | 브라우저 E2E 테스트 |
| V-6 | yt-dlp 미설치 시 ERROR 상태 + 명확한 메시지 | yt-dlp 제거 후 테스트 |
| V-7 | requirements.txt에 yt-dlp가 추가되었는지 | 파일 확인 |
| V-8 | asyncio.to_thread로 동기 yt-dlp를 비동기 래핑하는지 | 코드 확인 |
