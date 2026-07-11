# Weather - Typhoon Tracking

This repo stores typhoon tracking records as markdown files.

## Directory Structure

```
weather/
└── 颱風/
    └── {年份}/
        └── {月份}/
            └── {年份}_{中文名}_{國際命名}.md
```

## File Naming Convention

- Pattern: `{YYYY}_{中文名}_{國際命名}.md`
- Example: `2026_巴威_BAVI.md`

## File Format Rules

- All timestamps must include year and time (e.g. `2026/7/10 05:30`)
- Disaster severity tags: `🔴重大` `🟡警戒` `🟢一般`
- New developments are **appended** to the file, not overwritten
- Only update existing content if structurally necessary (e.g. correcting wrong data)

## Language

- File names and headers use Traditional Chinese (繁體中文)
- File content uses Traditional Chinese
