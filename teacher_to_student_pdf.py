"""
교사용 PDF → 학생용 PDF 변환기
파란색(답안) 텍스트와 도형(동그라미, 밑줄 등)을 제거하여 학생용 문제지로 변환합니다.
"""

import fitz  # PyMuPDF
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading


def is_blue_answer(color):
    """파란색 답안인지 확인 (정수 color 값)"""
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF

    # #00aeef, #00b9f2 등 시안/파란색 계열
    if r < 50 and b > 200 and g > 100:
        return True
    # 진한 파란색 (체크마크, 답안 표시 등)
    # B가 지배적이고 충분히 높은 경우
    if b > 120 and b > r * 3 and b > g * 2:
        return True
    return False


def is_blue_drawing(color_tuple):
    """도형의 색상이 파란색 답안 계열인지 확인 (RGB float 0~1 tuple)"""
    if not color_tuple or len(color_tuple) < 3:
        return False
    r, g, b = color_tuple[0], color_tuple[1], color_tuple[2]
    # 시안/파란색 계열: (0.0, 0.68, 0.94), (0.10, 0.69, 0.90) 등
    if r < 0.25 and b > 0.75 and g > 0.4:
        return True
    # 진한 파란색 (체크마크, 답안 표시 등): (0.13, 0.25, 0.60) 등
    if b > 0.45 and b > r * 3 and b > g * 2:
        return True
    return False


def convert_pdf(input_path, output_path, progress_callback=None):
    """교사용 PDF를 학생용으로 변환"""
    doc = fitz.open(input_path)
    total_pages = doc.page_count
    removed_count = 0

    for page_num in range(total_pages):
        page = doc[page_num]

        # 텍스트 블록 추출
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        redact_areas = []

        for block in blocks:
            if block["type"] == 0:  # 텍스트 블록
                for line in block["lines"]:
                    for span in line["spans"]:
                        color = span.get("color", 0)

                        if is_blue_answer(color):
                            bbox = fitz.Rect(span["bbox"])
                            redact_areas.append(bbox)
                            removed_count += 1

        # 파란색 도형(동그라미, 밑줄, 마킹 등) 제거
        drawings = page.get_drawings()
        for d in drawings:
            if is_blue_drawing(d.get("color")) or is_blue_drawing(d.get("fill")):
                redact_areas.append(fitz.Rect(d["rect"]))
                removed_count += 1

        # Redaction 적용 (흰색으로 덮기)
        for rect in redact_areas:
            page.add_redact_annot(rect, fill=(1, 1, 1))

        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)

        # 진행률 콜백
        if progress_callback:
            progress_callback(page_num + 1, total_pages)

    doc.save(output_path)
    doc.close()

    return total_pages, removed_count


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("교사용 → 학생용 PDF 변환기")
        self.root.geometry("500x300")
        self.root.resizable(False, False)

        # 메인 프레임
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 제목
        title_label = tk.Label(main_frame, text="교사용 PDF → 학생용 PDF 변환기",
                               font=("맑은 고딕", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # 설명
        desc_label = tk.Label(main_frame, text="파란색 답안(텍스트+도형)을 제거하여 학생용 문제지로 변환합니다.",
                              font=("맑은 고딕", 10))
        desc_label.pack(pady=(0, 20))

        # 파일 선택 버튼
        self.select_btn = tk.Button(main_frame, text="PDF 파일 선택",
                                    command=self.select_file,
                                    font=("맑은 고딕", 12),
                                    width=20, height=2)
        self.select_btn.pack(pady=10)

        # 선택된 파일 표시
        self.file_label = tk.Label(main_frame, text="선택된 파일: 없음",
                                   font=("맑은 고딕", 9), fg="gray")
        self.file_label.pack(pady=5)

        # 진행률 바
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.pack(pady=10)

        # 상태 표시
        self.status_label = tk.Label(main_frame, text="", font=("맑은 고딕", 10))
        self.status_label.pack(pady=5)

        # 결과 표시
        self.result_label = tk.Label(main_frame, text="", font=("맑은 고딕", 10), fg="green")
        self.result_label.pack(pady=5)

        self.input_path = None

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="교사용 PDF 선택",
            filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")]
        )

        if file_path:
            self.input_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"선택된 파일: {filename}")
            self.start_conversion()

    def start_conversion(self):
        if not self.input_path:
            return

        # 출력 파일명 생성
        dir_path = os.path.dirname(self.input_path)
        filename = os.path.basename(self.input_path)
        name, ext = os.path.splitext(filename)

        # (교사용) → (학생용) 변환
        if "(교사용)" in name:
            new_name = name.replace("(교사용)", "(학생용)")
        else:
            new_name = name + "_학생용"

        self.output_path = os.path.join(dir_path, new_name + ext)

        # UI 상태 변경
        self.select_btn.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_label.config(text="변환 중...")
        self.result_label.config(text="")

        # 백그라운드에서 변환 실행
        thread = threading.Thread(target=self.run_conversion)
        thread.start()

    def run_conversion(self):
        try:
            pages, removed = convert_pdf(
                self.input_path,
                self.output_path,
                progress_callback=self.update_progress
            )

            self.root.after(0, lambda: self.conversion_done(pages, removed))

        except Exception as e:
            self.root.after(0, lambda: self.conversion_error(str(e)))

    def update_progress(self, current, total):
        percent = (current / total) * 100
        self.root.after(0, lambda: self.progress.configure(value=percent))
        self.root.after(0, lambda: self.status_label.config(
            text=f"변환 중... {current}/{total} 페이지"))

    def conversion_done(self, pages, removed):
        self.select_btn.config(state=tk.NORMAL)
        self.status_label.config(text="변환 완료!")
        self.result_label.config(
            text=f"✓ {pages}페이지 처리, {removed}개 답안 제거\n저장: {os.path.basename(self.output_path)}"
        )

        messagebox.showinfo("완료",
            f"변환이 완료되었습니다!\n\n"
            f"처리: {pages}페이지\n"
            f"제거된 답안: {removed}개\n\n"
            f"저장 위치:\n{self.output_path}")

    def conversion_error(self, error_msg):
        self.select_btn.config(state=tk.NORMAL)
        self.status_label.config(text="오류 발생")
        self.result_label.config(text=error_msg, fg="red")
        messagebox.showerror("오류", f"변환 중 오류가 발생했습니다:\n{error_msg}")


def main():
    # 명령줄 인자로 파일이 주어진 경우 (드래그앤드롭)
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        if os.path.exists(input_path) and input_path.lower().endswith('.pdf'):
            dir_path = os.path.dirname(input_path)
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)

            if "(교사용)" in name:
                new_name = name.replace("(교사용)", "(학생용)")
            else:
                new_name = name + "_학생용"

            output_path = os.path.join(dir_path, new_name + ext)

            print(f"변환 중: {filename}")
            pages, removed = convert_pdf(input_path, output_path)
            print(f"완료! {pages}페이지, {removed}개 답안 제거")
            print(f"저장: {output_path}")
            return

    # GUI 모드
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
