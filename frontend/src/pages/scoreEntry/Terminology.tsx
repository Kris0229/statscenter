import { useState } from "react";
import { BookOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Term {
  term: string;
  desc: string;
}

const BATTING_TERMS: Term[] = [
  { term: "打序", desc: "打擊順序" },
  { term: "背號", desc: "球衣號碼" },
  { term: "PA", desc: "打席" },
  { term: "AB", desc: "打數" },
  { term: "SH", desc: "犧牲觸擊" },
  { term: "SF", desc: "高飛犧牲打" },
  { term: "BB", desc: "四壞球保送" },
  { term: "HP", desc: "觸身球" },
  { term: "IO", desc: "妨礙上壘／非打數上壘（依協會定義）" },
  { term: "TIE", desc: "其他特殊上壘（依協會定義）" },
  { term: "R", desc: "得分" },
  { term: "H", desc: "安打" },
  { term: "2B", desc: "二壘打" },
  { term: "3B", desc: "三壘打" },
  { term: "HR", desc: "全壘打" },
  { term: "RBI", desc: "打點" },
  { term: "SO", desc: "三振" },
  { term: "SB", desc: "盜壘成功" },
  { term: "CS", desc: "盜壘失敗" },
  { term: "GIDP", desc: "雙殺打" },
  { term: "E", desc: "失誤" },
];

const PITCHING_TERMS: Term[] = [
  { term: "背號", desc: "球衣號碼" },
  { term: "勝敗", desc: "決勝結果：W 勝／L 敗／SV 救援成功／BS 救援失敗／HLD 中繼成功／SVO 救援機會" },
  { term: "局數(outs)", desc: "投球局數，以出局數輸入（3 出局 = 1 局）" },
  { term: "NP", desc: "投球數" },
  { term: "BF", desc: "面對打者數" },
  { term: "AB", desc: "對方打數" },
  { term: "H", desc: "被安打" },
  { term: "HR", desc: "被全壘打" },
  { term: "BB", desc: "保送" },
  { term: "HP", desc: "觸身球" },
  { term: "SO", desc: "三振" },
  { term: "R", desc: "失分" },
  { term: "ER", desc: "自責分" },
  { term: "WP", desc: "暴投" },
  { term: "GS", desc: "先發" },
  { term: "CG", desc: "完投" },
  { term: "SHO", desc: "完封" },
  { term: "SV", desc: "救援成功" },
  { term: "SVO", desc: "救援機會" },
];

const LINE_SCORE_TERMS: Term[] = [
  { term: "E", desc: "失誤" },
  { term: "LOB", desc: "殘壘" },
];

function TermTable({ terms }: { terms: Term[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-28">縮寫</TableHead>
          <TableHead>說明</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {terms.map((t) => (
          <TableRow key={t.term}>
            <TableCell className="font-medium">{t.term}</TableCell>
            <TableCell>{t.desc}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function TerminologyDialog() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button type="button" variant="outline" onClick={() => setOpen(true)}>
        <BookOpen />
        術語對照表
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>術語縮寫對照表</DialogTitle>
          </DialogHeader>
          <div className="grid gap-6">
            <div>
              <h3 className="mb-2 text-sm font-semibold text-foreground">局數表</h3>
              <TermTable terms={LINE_SCORE_TERMS} />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-foreground">打擊</h3>
              <TermTable terms={BATTING_TERMS} />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-foreground">投手</h3>
              <TermTable terms={PITCHING_TERMS} />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
