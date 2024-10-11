import os
import sys
import blake3
import hashlib
import time
import re

def get_file_hash(file_path, algorithm):
    if algorithm == 'sha256':
        hash_algorithm = hashlib.sha256()
    elif algorithm == 'blake3':
        hash_algorithm = blake3.blake3()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    with open(file_path, 'rb') as f:
        while chunk := f.read(4096):
            hash_algorithm.update(chunk)

    return hash_algorithm.hexdigest()

def copy_file(source_file, dest_file, block_size):
    with open(source_file, 'rb') as src, open(dest_file, 'wb') as dst:
        while chunk := src.read(block_size):
            dst.write(chunk)

    stat_info = os.stat(source_file)
    os.utime(dest_file, (stat_info.st_atime, stat_info.st_mtime))

    try:
        os.setctime(dest_file, stat_info.st_ctime)
    except AttributeError:
        pass

def copy_directory_metadata(source_dir, dest_dir):
    stat_info = os.stat(source_dir)
    os.utime(dest_dir, (stat_info.st_atime, stat_info.st_mtime))
    
    try:
        os.setctime(dest_dir, stat_info.st_ctime)
    except AttributeError:
        pass

def should_exclude(path, exclude_patterns):
    return any(re.search(pattern, path) for pattern in exclude_patterns)

def backup_files(source_dir, dest_dir, algorithm, block_size, exclude_patterns):
    if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
        print(f"Исходный каталог не существует или не является директорией: {source_dir}")
        return

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        copy_directory_metadata(source_dir, dest_dir)

    total_files = 0
    hashed_files = 0
    start_time = time.time()
    hashes_per_second = 0
    hash_count = 0
    hash_start_time = time.time()

    print(f"Обработка файлов из каталога: {source_dir}")

    for dirpath, _, filenames in os.walk(source_dir):
        print(f"Обрабатываем каталог: {dirpath}")
        for filename in filenames:
            total_files += 1
            source_file = os.path.join(dirpath, filename)
            dest_file = os.path.join(dest_dir, os.path.relpath(source_file, source_dir))

            if should_exclude(source_file, exclude_patterns):
                print(f"Пропускаем файл/каталог: {source_file} (по исключению)")
                continue

            os.makedirs(os.path.dirname(dest_file), exist_ok=True)

            print(f"Вычисляем хэш для файла: {source_file}")
            start_hash_time = time.time()
            source_hash = get_file_hash(source_file, algorithm)
            hash_duration = time.time() - start_hash_time
            
            print(f"Текущий хэш для файла {source_file}: {source_hash}")
            hash_count += 1
            
            elapsed_hash_time = time.time() - hash_start_time
            if elapsed_hash_time >= 1.0:
                hashes_per_second = hash_count / elapsed_hash_time
                print(f"Скорость хэширования: {hashes_per_second:.2f} хэшей/с")
                hash_start_time = time.time()
                hash_count = 0

            if not os.path.exists(dest_file) or get_file_hash(dest_file, algorithm) != source_hash:
                print(f"Копируем файл: {source_file} -> {dest_file}")
                copy_file(source_file, dest_file, block_size)
                hashed_files += 1
            else:
                print(f"Файл не изменился: {source_file} (хэш совпадает)")

    end_time = time.time()
    total_duration = end_time - start_time
    print(f"Обработка завершена. Обработано файлов: {hashed_files}/{total_files}. Время: {total_duration:.2f} секунд.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python rolling.py <путь к исходному каталогу> <путь к целевому каталогу> [--algorithm sha256|blake3] [--block-size размер_в_байтах] [--exclude regex_pattern ...]")
        sys.exit(1)

    source_directory = sys.argv[1].strip('"')
    destination_directory = sys.argv[2].strip('"')
    algorithm = 'sha256'
    block_size = 4096
    exclude_patterns = []

    for i in range(3, len(sys.argv)):
        if sys.argv[i] == '--algorithm':
            algorithm = sys.argv[i + 1]
        elif sys.argv[i] == '--block-size':
            block_size = int(sys.argv[i + 1])
        elif sys.argv[i] == '--exclude':
            exclude_patterns = sys.argv[i + 1:]

    print(f"Исходный каталог: {source_directory}")
    print(f"Целевой каталог: {destination_directory}")
    print(f"Исключения: {exclude_patterns}")

    backup_files(source_directory, destination_directory, algorithm, block_size, exclude_patterns)