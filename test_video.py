from apps.dashboard.models import Lesson
import os
l = Lesson.objects.filter(title__icontains='PPE Video Analytics').first()
if l:
    print(f'Title: {l.title}')
    print(f'File URL: {l.video_file_path.url if l.video_file_path else None}')
    print(f'Exists: {os.path.exists(l.video_file_path.path) if l.video_file_path else False}')
else:
    print('Lesson not found')
