import { useMutation } from "@tanstack/react-query";
import { Download, FileDown, FileSpreadsheet } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useCan } from "../context/OrgContext";
import { api, ApiError, toApiError } from "../services/apiClient";
import { saveBlob } from "../services/finance";
import { Popover } from "./ui/Popover";
import { useToast } from "./ui/Toast";

type FileType = "xlsx" | "csv";
type Params = Record<string, string | number | boolean | undefined | null>;

/** Fetches `<path>download/` with the list's current filters and saves the file. */
async function downloadList(path: string, params: Params, file: FileType) {
  const query = Object.fromEntries(
    Object.entries(params).filter(
      ([key, value]) =>
        key !== "page" && value !== undefined && value !== null && value !== "",
    ),
  );
  try {
    const response = await api.get<Blob>(`${path}download/`, {
      params: { ...query, file },
      responseType: "blob",
    });
    const name =
      /filename="([^"]+)"/.exec(
        String(response.headers["content-disposition"] ?? ""),
      )?.[1] ?? `download.${file}`;
    saveBlob(response.data, name);
  } catch (error) {
    // Errors come back as a Blob too; read the JSON message out of it.
    const response = (
      error as { response?: { status: number; data?: unknown } }
    ).response;
    if (response?.data instanceof Blob) {
      const body = JSON.parse(await response.data.text().catch(() => "{}")) as {
        error?: { code: string; message: string };
      };
      if (body.error)
        throw new ApiError(
          response.status,
          body.error.code,
          body.error.message,
        );
    }
    throw error;
  }
}

/** "Download" button for a list page: Excel or CSV of everything the list shows with its current filters. */
export function DownloadMenu({
  path,
  params = {},
}: {
  path: string;
  params?: Params;
}) {
  const { t } = useTranslation();
  const { notify } = useToast();
  const allowed = useCan("reports.export");
  const download = useMutation({
    mutationFn: (file: FileType) => downloadList(path, params, file),
    onError: (error) =>
      notify(toApiError(error).message || t("errors.generic"), "error"),
  });
  if (!allowed) return null;
  return (
    <Popover
      label={t("common.download")}
      align="right"
      trigger={() => (
        <span className="inline-flex h-10 items-center gap-2 rounded-lg bg-white px-4 text-sm font-medium text-slate-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
          <Download
            className={download.isPending ? "size-4 animate-pulse" : "size-4"}
            aria-hidden
          />{" "}
          {t("common.download")}
        </span>
      )}
    >
      {(close) => (
        <>
          {(["xlsx", "csv"] as FileType[]).map((file) => (
            <button
              key={file}
              type="button"
              role="menuitem"
              disabled={download.isPending}
              onClick={() => (close(), download.mutate(file))}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-50"
            >
              {file === "xlsx" ? (
                <FileSpreadsheet className="size-4 text-emerald-700" />
              ) : (
                <FileDown className="size-4 text-slate-600" />
              )}
              {t(file === "xlsx" ? "download.excel" : "download.csv")}
            </button>
          ))}
        </>
      )}
    </Popover>
  );
}
