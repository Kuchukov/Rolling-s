import os
import sys
import blake3
import hashlib
import time
import re

def get_file_hash(file_path, algorithm):
    """Вычисляет хэш файла с использованием указанного алгоритма."""
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
    """Копирует файл с указанным размером блока и сохраняет метаданные."""
    with open(source_file, 'rb') as src, open(dest_file, 'wb') as dst:
        while chunk := src.read(block_size):
            dst.write(chunk)

    # Копируем метаданные времени
    stat_info = os.stat(source_file)
    os.utime(dest_file, (stat_info.st_atime, stat_info.st_mtime))

    try:
        os.setctime(dest_file, stat_info.st_ctime)
    except AttributeError:
        # Если система не поддерживает изменение времени создания
        pass

def copy_directory_metadata(source_dir, dest_dir):
    """Копирует метаданные каталога, такие как время доступа, модификации и создания."""
    stat_info = os.stat(source_dir)
    os.utime(dest_dir, (stat_info.st_atime, stat_info.st_mtime))
    
    try:
        os.setctime(dest_dir, stat_info.st_ctime)
    except AttributeError:
        pass

def should_exclude(path, exclude_patterns):
    """Проверяет, нужно ли исключить файл или каталог на основе заданных шаблонов."""
    return any(re.search(pattern, path) for pattern in exclude_patterns)

def backup_files(source_dir, dest_dir, algorithm, block_size, exclude_patterns):
    """Копирует файлы и метаданные с одного устройства на другое, исключая указанные файлы."""
    # Преобразуем пути в абсолютные
    source_dir = os.path.abspath(source_dir)
    dest_dir = os.path.abspath(dest_dir)

    # Проверяем, что исходный каталог существует и является директорией
    if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
        print(f"Исходный каталог не существует или не является директорией: {source_dir}")
        return

    # Создаем целевой каталог, если он не существует
    if not os.path.exists(dest_dir):
        print(f"Целевой каталог не существует: {dest_dir}. Создание каталога.")
        os.makedirs(dest_dir)
        copy_directory_metadata(source_dir, dest_dir)

    total_files = 0
    copied_files = 0
    start_time = time.time()

    print(f"Начало архивного копирования с устройства: {source_dir}")

    # Проход по всем подкаталогам и файлам в исходном каталоге
    for dirpath, dirnames, filenames in os.walk(source_dir):
        rel_dirpath = os.path.relpath(dirpath, source_dir)
        target_dirpath = os.path.join(dest_dir, rel_dirpath)

        # Создаем каталог в целевом месте, если он еще не существует
        if not os.path.exists(target_dirpath):
            os.makedirs(target_dirpath)
            copy_directory_metadata(dirpath, target_dirpath)

        # Копируем файлы из текущего каталога
        for filename in filenames:
            total_files += 1
            source_file = os.path.join(dirpath, filename)
            dest_file = os.path.join(dest_dir, os.path.relpath(source_file, source_dir))

            # Пропускаем файлы, которые соответствуют шаблонам исключения
            if should_exclude(source_file, exclude_patterns):
                print(f"Пропускаем файл/каталог: {source_file} (по исключению)")
                continue

            # Создаем каталог для файла, если его еще нет
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)

            # Копируем файл, если его нет в целевом каталоге или он отличается
            if not os.path.exists(dest_file) or get_file_hash(dest_file, algorithm) != get_file_hash(source_file, algorithm):
                print(f"Копируем файл: {source_file} -> {dest_file}")
                copy_file(source_file, dest_file, block_size)
                copied_files += 1
            else:
                print(f"Файл не изменился: {source_file} (хэш совпадает)")

    end_time = time.time()
    total_duration = end_time - start_time
    print(f"Архивное копирование завершено. Обработано файлов: {copied_files}/{total_files}. Время: {total_duration:.2f} секунд.")

if __name__ == "__main__":
    # Проверяем правильность аргументов командной строки
    if len(sys.argv) < 3:
        print("Использование: python backup.py <источник> <пункт назначения> [--algorithm sha256|blake3] [--block-size размер_в_байтах] [--exclude regex_pattern ...]")
        sys.exit(1)

    source_directory = sys.argv[1].strip('"')
    destination_directory = sys.argv[2].strip('"')
    algorithm = 'sha256'
    block_size = 4096
    exclude_patterns = []

    # Обрабатываем опции командной строки
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

    # Запускаем процесс архивного копирования
    backup_files(source_directory, destination_directory, algorithm, block_size, exclude_patterns)