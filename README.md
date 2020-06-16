# Lynda Downloader

**A cli tool for downloading courses from lynda.com, with concurrency.**

## Requirements Installation

```
pip install -r requirements.txt
```

## Usage

**Download course by URL concurrently**

```
python3 main.py -u COURSE_URL --concurrent
```

or
**Download course by a text file containing a list of URLs**

```
python3 main.py -f /path/to/text/file --concurrent
```

or
**Download course by URL synchronously, if without good CPU and large memory**

```
python3 main.py -u COURSE_URL
```

## License

**MIT**
