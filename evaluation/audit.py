"""Check the campus-life guides through the same answer path as the offline CLI."""
import json

from campus.knowledge import Knowledge
from campus.service import Offline, Session


COMMON_QUESTIONS = (
    ("{name}的办理流程是什么？", "办理流程"),
    ("{name}的入口是什么？", "申请入口"),
    ("{name}需要什么材料？", "所需材料"),
)
DETAIL_QUESTIONS = (
    ("办理地点", "{name}该去哪个窗口？"),
    ("开放时间", "{name}几点开始？"),
    ("办理费用", "{name}的费用是多少？"),
)
SPOKEN_QUESTIONS = (
    ("这学期什么时候放假？", "academic-calendar", "教学周"),
    ("周末图书馆开到几点？", "library-hours", "09:00–21:00"),
    ("周六有校车吗？", "campus-shuttle", "09:00、16:30"),
    ("食堂周六开吗？", "dining-hours", "07:30 开门"),
    ("寝室停电了怎么办？", "dorm-electricity", "余额正常却停电"),
    ("宿舍厕所堵了怎么办？", "dorm-repair", "方便上门的时段"),
    ("宿舍房门打不开", "dorm-access", "本楼宿管"),
    ("我要拿毕业证", "certificate-pickup", "补领"),
    ("上课的教室在哪", "schedule-query", "单双周"),
    ("哪个教室可以自习", "study-room-booking", "空闲时段"),
    ("英语考试要推迟", "exam-deferral", "缓考原因证明"),
    ("挂科了要怎么重修", "course-retake", "可选班"),
    ("挂科成绩有问题想复核", "grade-review", "受理号"),
    ("学费付了但是显示没交", "tuition-payment", "缴费记录"),
    ("想取消体育馆预约", "sports-booking", "取消预约"),
    ("校园卡没钱了", "card-topup", "订单状态"),
    ("校园卡扣了两次钱", "card-transaction", "交易编号"),
    ("快递到了去哪里拿", "courier-pickup", "取件码"),
    ("校园网连接不上怎么办", "wifi-troubleshooting", "设备类型"),
    ("门诊几点开门", "clinic-visit", "08:30–11:30"),
    ("我该怎么预约学校的心理老师", "mental-health-booking", "预约"),
    ("想找校内兼职", "work-study", "岗位报名表"),
    ("我要退宿怎么办", "dorm-checkout", "归还钥匙"),
    ("怎么开发票", "tuition-invoice", "票据抬头"),
    ("怎么查毕业档案寄没寄", "student-file", "签收状态"),
)


def main():
    kb = Knowledge()
    if kb.errors or not kb.catalog:
        raise SystemExit(f"指南校验失败：{kb.errors}")
    failures = []
    checked = 0

    def check(engine, session, query, guide_id, *, section=None, text=None):
        nonlocal checked
        checked += 1
        turn = engine.ask(query, session)
        citations = turn.citations
        if (not citations or session.guide_id != guide_id
                or any(row["guide_id"] != guide_id for row in citations)
                or section and not any(row["section"] == section for row in citations)
                or text and text not in turn.answer
                or "无法核实" in turn.answer):
            failures.append({"mode": engine.mode, "query": query, "guide": guide_id,
                             "section": section, "answer": turn.answer})

    for mode in ("rag", "full"):
        engine = Offline(kb, mode)
        for guide_id, meta in kb.catalog.items():
            rows = {row["section"]: row["text"] for row in kb.read(guide_id)["evidence"]}
            # A bare title should give the guide's actionable steps or the detail named in its title.
            check(engine, Session(), meta.name, guide_id)
            for template, section in COMMON_QUESTIONS:
                text = "没有列出需提交的材料" if section == "所需材料" and not meta.materials else None
                check(engine, Session(), template.format(name=meta.name), guide_id, section=section, text=text)
            for section, template in DETAIL_QUESTIONS:
                if section in rows:
                    check(engine, Session(), template.format(name=meta.name), guide_id, section=section)
        for query, guide_id, expected in SPOKEN_QUESTIONS:
            check(engine, Session(), query, guide_id, text=expected)
        session = Session()
        check(engine, session, "宿舍厕所堵了怎么办？", "dorm-repair", text="工单")
        check(engine, session, "怎么查处理进度？", "dorm-repair", text="工单列表")
        check(engine, session, "改问校园卡扣了两次钱", "card-transaction", text="消费异议")

    print(json.dumps({"guides": len(kb.catalog), "checked": checked,
                      "passed": checked - len(failures), "failures": failures},
                     ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
