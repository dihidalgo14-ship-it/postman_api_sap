import pandas as pd
from tkinter import Tk, filedialog, messagebox
import os

def seleccionar_archivo(titulo):
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title=titulo,
        filetypes=[("Excel/CSV", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")]
    )
    root.destroy()
    return path

def leer_archivo(path):
    if path.endswith(".csv"):
        return pd.read_csv(path, dtype=str)
    else:
        return pd.read_excel(path, dtype=str)

def main():
    print("=" * 55)
    print("  Cruce BP + Emails - SAP Business Partner")
    print("=" * 55)

    # ── Archivo 1: Emails (AddressID + EmailAddress) ──────
    print("\n[1] Selecciona el archivo de EMAILS")
    print("    (contiene: AddressID, EmailAddress, ...)")
    path1 = seleccionar_archivo("Archivo 1 - Emails (A_AddressEmailAddress)")
    if not path1:
        print("Cancelado.")
        return

    df_emails = leer_archivo(path1)
    print(f"    ✓ {len(df_emails)} filas cargadas | Columnas: {list(df_emails.columns)}")

    # Validar columnas necesarias
    if "AddressID" not in df_emails.columns or "EmailAddress" not in df_emails.columns:
        print("\n[ERROR] El archivo de emails debe tener columnas 'AddressID' y 'EmailAddress'")
        input("Presiona Enter para salir...")
        return

    # Solo las columnas que interesan
    df_emails = df_emails[["AddressID", "EmailAddress"]].copy()
    df_emails = df_emails[df_emails["EmailAddress"].notna() & (df_emails["EmailAddress"].str.strip() != "")]
    df_emails["AddressID"] = df_emails["AddressID"].str.strip()

    print(f"    ✓ {len(df_emails)} emails válidos (sin vacíos)")

    # ── Archivo 2: Business Partners (con AddressID) ──────
    print("\n[2] Selecciona el archivo de BUSINESS PARTNERS")
    print("    (contiene: BusinessPartner, AddressID, ...)")
    path2 = seleccionar_archivo("Archivo 2 - Business Partners (A_BusinessPartnerAddress)")
    if not path2:
        print("Cancelado.")
        return

    df_bp = leer_archivo(path2)
    print(f"    ✓ {len(df_bp)} filas cargadas | Columnas: {list(df_bp.columns)}")

    # Detectar columna AddressID en archivo 2 (puede llamarse diferente)
    col_address = None
    for col in df_bp.columns:
        if "address" in col.lower() and "id" in col.lower():
            col_address = col
            break
    if col_address is None:
        # Tomar la segunda columna como fallback (según indicación del usuario)
        col_address = df_bp.columns[1]
        print(f"    ⚠ No se encontró 'AddressID', usando segunda columna: '{col_address}'")
    else:
        print(f"    ✓ Columna AddressID detectada: '{col_address}'")

    df_bp[col_address] = df_bp[col_address].astype(str).str.strip()

    # ── Cruce (LEFT JOIN: todos los BP, con todos sus emails) ─
    print("\n[3] Cruzando tablas...")
    df_resultado = df_bp.merge(
        df_emails,
        left_on=col_address,
        right_on="AddressID",
        how="left"
    )

    # Limpiar columna AddressID duplicada si se creó
    if "AddressID_x" in df_resultado.columns:
        df_resultado = df_resultado.rename(columns={"AddressID_x": col_address})
        df_resultado = df_resultado.drop(columns=["AddressID_y"], errors="ignore")

    total_bp        = len(df_bp)
    bp_con_email    = df_resultado["EmailAddress"].notna().sum()
    bp_sin_email    = df_resultado["EmailAddress"].isna().sum()
    address_multi   = df_emails.groupby("AddressID").size()
    casos_multi     = (address_multi > 1).sum()

    print(f"\n  Resultados:")
    print(f"  ├─ Filas en tabla BP:              {total_bp}")
    print(f"  ├─ Filas con email encontrado:     {bp_con_email}")
    print(f"  ├─ Filas sin email (vacío):        {bp_sin_email}")
    print(f"  ├─ AddressID con múltiples emails: {casos_multi}")
    print(f"  └─ Total filas resultado:          {len(df_resultado)}")

    # ── Guardar resultado ─────────────────────────────────
    print("\n[4] Selecciona dónde guardar el archivo resultado...")
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    out_path = filedialog.asksaveasfilename(
        title="Guardar resultado",
        defaultextension=".xlsx",
        filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
        initialfile="BP_con_emails_cruzados.xlsx"
    )
    root.destroy()

    if not out_path:
        print("Cancelado.")
        return

    if out_path.endswith(".csv"):
        df_resultado.to_csv(out_path, index=False, encoding="utf-8-sig")
    else:
        df_resultado.to_excel(out_path, index=False)

    print(f"\n  ✓ Archivo guardado: {out_path}")
    print(f"  ✓ {len(df_resultado)} filas totales")
    print("\n" + "=" * 55)
    input("  Listo. Presiona Enter para cerrar...")

if __name__ == "__main__":
    main()