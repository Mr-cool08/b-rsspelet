from datetime import date, datetime, time

from stockfight import ngm_history


_CSV = """Trading date and Time,Instrument identification code,Price,Venue of execution,Price currency,Type,Publication date and time
2026-04-30T09:17:01.400Z,SE0001057910,2.6450,XNGM,SEK,,2026-04-30T09:17:04.400Z
2026-04-30T08:15:29.133Z,SE0001057910,2.6200,XNGM,SEK,,2026-04-30T08:15:29.133Z
2026-04-30T08:10:00.000Z,SE0008588131,12.1500,NSME,SEK,,2026-04-30T08:10:00.000Z
2026-04-30T08:10:00.000Z,SE0008588131,1.1500,XNGM,SEK,,2026-04-30T08:10:00.000Z
2026-04-30T08:11:00.000Z,SE0013382546,182.0000,XNGM,EUR,,2026-04-30T08:11:00.000Z
2026-04-30T08:12:00.000Z,SE0013382546,182.0000,XNGM,SEK,CANC,2026-04-30T08:12:00.000Z
2026-04-30T12:00:00.000Z,SE0013382546,182.0000,XNGM,SEK,,2026-04-30T12:00:00.000Z
"""
_CALENDAR = """<table>
<tr><td>2026-04-30</td><td>Valborgsmässoafton</td><td><strong>Halvdag</strong></td></tr>
</table>"""


def test_ngm_reads_delayed_reports_at_publication_time_and_keeps_sessions_across_restarts(tmp_path, monkeypatch):
    responses = {
        ngm_history._REPORTS: '["2026-05-01", "2026-04-30"]',
        f"{ngm_history._REPORTS}/2026-04-30": _CSV,
        ngm_history._CALENDAR: _CALENDAR,
    }
    history = ngm_history.NgmHistory(tmp_path)
    monkeypatch.setattr(history, "_get", responses.__getitem__)
    session = history.session_before(date(2026, 5, 1))

    assert session.day == date(2026, 4, 30)
    assert (session.opens, session.closes) == (time(9), time(13))
    assert session.quotes == {
        "SOSI": [(datetime.fromisoformat("2026-04-30T08:15:29.133Z").timestamp(), 262),
                 (datetime.fromisoformat("2026-04-30T09:17:04.400Z").timestamp(), 265)],
        "BRIX": [(datetime.fromisoformat("2026-04-30T08:10:00Z").timestamp(), 1215)],
    }

    restarted_history = ngm_history.NgmHistory(tmp_path)
    responses = {
        ngm_history._REPORTS: '["2026-05-04", "2026-05-03", "2026-05-02"]',
    }
    monkeypatch.setattr(restarted_history, "_get", responses.__getitem__)
    assert restarted_history.session_before(date(2026, 5, 4)) == session
