import io

from ofxtools.Parser import OFXTree

from apps.imports.parsers import ParsedRow


def parse_ofx(file_bytes: bytes) -> list[ParsedRow]:
    """
    OFX is self-describing -- no column mapping needed. STMTTRN.trnamt
    already matches our normalized signed-amount convention exactly
    (positive = money in, negative = money out), so no sign translation
    happens here, unlike the CSV path. FITID is used verbatim as
    external_id -- the format's own spec guarantees per-account uniqueness,
    exactly the granularity our dedup constraint needs.
    """
    tree = OFXTree()
    tree.parse(io.BytesIO(file_bytes))
    ofx = tree.convert()

    parsed_rows = []
    for statement in ofx.statements:
        for txn in statement.transactions:
            parsed_rows.append(
                ParsedRow(
                    transaction_date=txn.dtposted.date(),
                    description=txn.name or "",
                    amount=txn.trnamt,
                    memo=txn.memo or "",
                    running_balance=None,  # OFX balances are statement-level, not per-row
                    external_id=txn.fitid,
                    raw_row={
                        "fitid": txn.fitid,
                        "trntype": str(txn.trntype) if txn.trntype else "",
                        "name": txn.name or "",
                        "memo": txn.memo or "",
                    },
                )
            )
    return parsed_rows
