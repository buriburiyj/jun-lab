import os
import time
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def bubble_sort(arr):
    a = arr[:]
    n = len(a)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


def insertion_sort(arr):
    a = arr[:]
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a


def selection_sort(arr):
    a = arr[:]
    for i in range(len(a)):
        min_idx = i
        for j in range(i + 1, len(a)):
            if a[j] < a[min_idx]:
                min_idx = j
        a[i], a[min_idx] = a[min_idx], a[i]
    return a


def merge_sort(arr):
    if len(arr) <= 1:
        return arr[:]
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def quick_sort(arr):
    if len(arr) <= 1:
        return arr[:]
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)


def timsort(arr):
    return sorted(arr)


ALGORITHMS = {
    "Bubble Sort": bubble_sort,
    "Insertion Sort": insertion_sort,
    "Selection Sort": selection_sort,
    "Merge Sort": merge_sort,
    "Quick Sort": quick_sort,
    "Timsort (built-in)": timsort,
}

SIZES = [100, 500, 1000, 2000, 5000]
TRIALS = 3


def benchmark():
    results = {name: [] for name in ALGORITHMS}
    header = f"{'Algorithm':<26} {'Size':<8} {'Avg Time (sec)':<18} {'Avg Time (ms)':<16}"
    print(header)
    print("-" * len(header))

    for size in SIZES:
        base = [random.randint(0, 100000) for _ in range(size)]
        for name, func in ALGORITHMS.items():
            elapsed_list = []
            for _ in range(TRIALS):
                data = base[:]
                start = time.perf_counter()
                func(data)
                end = time.perf_counter()
                elapsed_list.append(end - start)
            avg_sec = sum(elapsed_list) / len(elapsed_list)
            results[name].append(avg_sec)
            print(f"{name:<26} {size:<8} {avg_sec:<18.6f} {avg_sec * 1000:<16.3f}")

    return results, SIZES


def plot_results(results, sizes):
    os.makedirs("out", exist_ok=True)
    plt.figure(figsize=(10, 6))
    for name, times in results.items():
        plt.plot(sizes, times, marker="o", label=name)
    plt.xlabel("Input Size")
    plt.ylabel("Average Time (seconds)")
    plt.title("Sorting Algorithm Speed Comparison")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig("out/sorting_comparison.png")
    print("\nGraph saved to: out/sorting_comparison.png")


if __name__ == "__main__":
    random.seed(42)
    results, sizes = benchmark()
    plot_results(results, sizes)
