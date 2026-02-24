-- report_brief: 기본 탭용 한줄 요약 (수급|회사근황|사야하나?)
ALTER TABLE analysis_cache ADD COLUMN IF NOT EXISTS report_brief TEXT DEFAULT '';
