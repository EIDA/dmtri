---
tags:
  - node-operator
---

# dmtri: Troubleshooting

## A PSD is still missing after `dmtri fix --psd`

Look at the dmtri summary. It shows what seedpsd said.

| You see | What it means | What to do |
|---|---|---|
| `no SDS files in ...` | The data is not on the seedpsd machine. | Check `seedpsd_archive` in `hosts.ini`. |
| `Shorter than the 'ppsd_length'` | The data is in small pieces. A PSD needs at least one hour of data without gaps. | Nothing. If every piece is shorter than an hour, no PSD can be made. |
| `Unknown data source` | seedpsd has no metadata for this channel. | Run `seedpsd-cli metadata update --network <N> --station <S> --channel <C>`, then fix again. |
| `Too many 'source'` | seedpsd has the same channel twice in its database. | Ask the seedpsd admin to remove the duplicate. |

If `seedpsd-cli metadata update` fails with `relation "network_XX.epoch" does not exist`, the network was never set up in seedpsd. Ask the seedpsd admin.
