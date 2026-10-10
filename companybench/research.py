"""Read-only research navigation; artifact readiness never grants approval."""
from pathlib import Path
from .core import read_json, contained


def research_summary(project, records):
    root = Path(project)
    path = root / 'work/research-navigation.json'
    if not path.is_file():
        return {'configured': False, 'stages': [], 'next_step': '按实际合同补研究导航；原项目证据和历史保留'}
    plan = read_json(path)
    lookup = {r['id']: r for r in records}
    stages = []
    for row in plan.get('stages', []):
        files = []
        for relative in row.get('files', []):
            try:
                exists = contained(root, relative).is_file()
            except ValueError:
                exists = False
                # Invalid paths are not offered as browser links.
                relative = ''
            files.append({'path': relative, 'exists': exists})
        ids = row.get('record_ids', [])
        ineffective = [rid for rid in ids if lookup.get(rid, {}).get('effective_state') != 'Fact']
        stages.append({
            'id': row['id'], 'title': row['title'], 'question': row.get('question', ''),
            'files': files, 'work_status': row.get('work_status', '未开始'),
            'note': row.get('note', ''), 'ineffective_record_ids': ineffective,
            'readiness': '依据需重核' if ineffective else '文件待准备' if any(not f['exists'] for f in files) else '文件可阅读；内容状态另查',
        })
    next_row = next((r for r in stages if r['work_status'] != '底稿完成' or r['ineffective_record_ids']), None)
    return {'configured': True, 'stages': stages,
            'next_step': next_row['question'] if next_row else '审阅报告、Unknown与实际签署；文件齐备不等于验收通过',
            'network_policy': plan.get('network_policy', ''),
            'final_judgment': plan.get('final_judgment', '人工确认')}
