"""Generación de PDFs mínimos para que los e2e no dependan de archivos externos."""


def make_pdf(marker: str, padding_bytes: int = 0) -> bytes:
    """Crear un PDF válido de una página, con texto único y padding opcional."""
    texto = "".join(caracter for caracter in marker if caracter.isalnum()) or "prueba"
    contenido = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("ascii")
    contenido += b" " * padding_bytes

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(contenido)).encode("ascii") + b" >>\nstream\n"
        + contenido
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for numero, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{numero} 0 obj\n".encode("ascii"))
        pdf.extend(objeto)
        pdf.extend(b"\nendobj\n")

    inicio_xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
