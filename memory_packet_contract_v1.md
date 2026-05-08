{\rtf1\ansi\deff3\adeflang1025
{\fonttbl{\f0\froman\fprq2\fcharset0 Times New Roman;}{\f1\froman\fprq2\fcharset2 Symbol;}{\f2\fswiss\fprq2\fcharset0 Arial;}{\f3\froman\fprq2\fcharset0 Liberation Serif{\*\falt Times New Roman};}{\f4\fswiss\fprq2\fcharset0 Liberation Sans{\*\falt Arial};}{\f5\fnil\fprq2\fcharset0 Microsoft YaHei;}{\f6\fnil\fprq2\fcharset0 Lucida Sans;}{\f7\fswiss\fprq0\fcharset128 Lucida Sans;}}
{\colortbl;\red0\green0\blue0;\red0\green0\blue255;\red0\green255\blue255;\red0\green255\blue0;\red255\green0\blue255;\red255\green0\blue0;\red255\green255\blue0;\red255\green255\blue255;\red0\green0\blue128;\red0\green128\blue128;\red0\green128\blue0;\red128\green0\blue128;\red128\green0\blue0;\red128\green128\blue0;\red128\green128\blue128;\red192\green192\blue192;}
{\stylesheet{\s0\snext0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052 Normal;}
{\s15\sbasedon0\snext16\rtlch\af6\afs28 \ltrch\hich\af4\loch\sb240\sa120\keepn\f4\fs28\dbch\af5 Heading;}
{\s16\sbasedon0\snext16\loch\sl276\slmult1\sb0\sa140 Body Text;}
{\s17\sbasedon16\snext17\rtlch\af7 \ltrch List;}
{\s18\sbasedon0\snext18\rtlch\af7\afs24\ai \ltrch\loch\sb120\sa120\noline\fs24\i caption;}
{\s19\sbasedon0\snext19\rtlch\af7 \ltrch\loch\noline Index;}
}{\*\generator LibreOffice/25.2.7.2$Windows_X86_64 LibreOffice_project/5cbfd1ab6520636bb5f7b99185aa69bd7456825d}{\info{\creatim\yr2026\mo4\dy30\hr22\min13}{\revtim\yr2026\mo4\dy30\hr22\min14}{\printim\yr0\mo0\dy0\hr0\min0}}{\*\userprops}\deftab709
\hyphauto1\viewscale80\formshade\nobrkwrptbl\paperh15840\paperw12240\margl1134\margr1134\margt1134\margb1134\sectd\sbknone\sftnnar\saftnnrlc\sectunlocked1\pgwsxn12240\pghsxn15840\marglsxn1134\margrsxn1134\margtsxn1134\margbsxn1134\ftnbj\ftnstart1\ftnrstcont\ftnnar\fet\aftnrstcont\aftnstart1\aftnnrlc
{\*\ftnsep\chftnsep}\pgndec\pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Memory Packet Contract v1}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## Purpose}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Defines the canonical runtime memory unit.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
This is the standard retrieval object used by the runtime memory system.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
It creates the architectural seam between:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- current runtime retrieval}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- future event compression}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- future Neo4j knowledge supply}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
This contract governs memory shape.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
It does not govern storage implementation.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## Core Principle}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Memory is not authority.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Continuity remains authority.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Memory provides:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- context}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- reinforcement}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- retrieval support}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Continuity provides truth.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Memory Packet Structure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## Required Fields}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### packet_id}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
string}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Unique packet identity.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### packet_type}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
enum}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Allowed:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- continuity}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- event}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- relationship}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- character}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- conflict}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- world}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- authored}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- knowledge}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Defines memory domain.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### source_type}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
enum}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Allowed:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- continuity_state}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- authored_source}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- event_packet}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- runtime_observation}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- knowledge_graph}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Tracks origin.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### source_ref}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
string}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Traceable source identifier.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Examples:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- continuity key}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- authored file path}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- graph node id}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### authority_level}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
enum}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Allowed:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- canonical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- derived}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- advisory}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definitions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
canonical:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
truth-bearing}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
derived:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
processed from canonical truth}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
advisory:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
retrieval suggestion only}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### memory_scope}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
enum}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Allowed:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- immediate}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- scene}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- arc}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- global}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Defines operational range.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### relevance_scores}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
object}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Required fields:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
goal_relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
emotional_relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
relationship_relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
location_relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
conflict_relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
continuity_relevance}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Range:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
0.0\u8211\'961.0}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Retrieval scoring.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### content_payload}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
object}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
The actual memory content.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Shape depends on packet_type.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### created_at}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
timestamp}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Memory creation time.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### last_accessed_at}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
timestamp}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Last retrieval access.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### expiration_policy}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
enum}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Allowed:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- none}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- scene_end}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- arc_end}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- dynamic_decay}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Lifecycle behavior.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
### retrieval_reason}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
string}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Why this memory was selected.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Required for audit visibility.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Optional Fields}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## related_entities}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
array}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Linked actors/entities.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## related_events}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
array}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Connected event references.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## emotional_weight}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
float}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Range:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
0.0\u8211\'961.0}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Emotional significance.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## conflict_weight}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
float}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Range:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
0.0\u8211\'961.0}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Conflict significance.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## decay_score}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Type:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
float}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Range:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
0.0\u8211\'961.0}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Dynamic relevance decay.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Packet Type Definitions}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# continuity}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Truth-bearing continuity facts.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
canonical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# event}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Compressed historical event.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
derived}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# relationship}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Relationship state and deltas.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
derived or canonical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# character}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Identity truths, motivations, values.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
canonical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# conflict}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Active unresolved tensions.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
derived}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# world}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Lore, setting rules, environmental truth.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
canonical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# authored}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Static authored source material.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
canonical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# knowledge}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Purpose:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Neo4j-supplied graph knowledge.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Authority:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
derived or advisory}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Retrieval Rules}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 1:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Canonical packets outrank advisory packets.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 2:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Higher relevance outranks lower relevance.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 3:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Immediate scope outranks broader scope when equal.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 4:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Conflict-active packets receive temporary weight boosts.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 5:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Recent packets receive temporary relevance boosts.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Audit Requirements}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Every retrieved memory packet must record:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- packet_id}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- source_type}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- source_ref}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- authority_level}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- retrieval_reason}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- final score}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Required for observability.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Compatibility Requirements}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Current system compatibility:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Must support adaptation from:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- continuity state}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- authored retrieval bundles}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- runtime event summaries}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Future compatibility:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Must support:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- event packet ingestion}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- Neo4j knowledge retrieval}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Non-Goals}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
This contract does not define:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- storage engine}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- retrieval algorithm}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- compression strategy}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- graph schema}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Those belong to later contracts.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Future Dependent Contracts}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Depends into:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- Event Packet Contract v1}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- Knowledge Entry Contract v1}
\par }