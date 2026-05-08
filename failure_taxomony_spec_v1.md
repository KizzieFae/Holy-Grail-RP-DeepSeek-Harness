{\rtf1\ansi\deff3\adeflang1025
{\fonttbl{\f0\froman\fprq2\fcharset0 Times New Roman;}{\f1\froman\fprq2\fcharset2 Symbol;}{\f2\fswiss\fprq2\fcharset0 Arial;}{\f3\froman\fprq2\fcharset0 Liberation Serif{\*\falt Times New Roman};}{\f4\fswiss\fprq2\fcharset0 Liberation Sans{\*\falt Arial};}{\f5\fnil\fprq2\fcharset0 Microsoft YaHei;}{\f6\fnil\fprq2\fcharset0 Lucida Sans;}{\f7\fswiss\fprq0\fcharset128 Lucida Sans;}}
{\colortbl;\red0\green0\blue0;\red0\green0\blue255;\red0\green255\blue255;\red0\green255\blue0;\red255\green0\blue255;\red255\green0\blue0;\red255\green255\blue0;\red255\green255\blue255;\red0\green0\blue128;\red0\green128\blue128;\red0\green128\blue0;\red128\green0\blue128;\red128\green0\blue0;\red128\green128\blue0;\red128\green128\blue128;\red192\green192\blue192;}
{\stylesheet{\s0\snext0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052 Normal;}
{\s15\sbasedon0\snext16\rtlch\af6\afs28 \ltrch\hich\af4\loch\sb240\sa120\keepn\f4\fs28\dbch\af5 Heading;}
{\s16\sbasedon0\snext16\loch\sl276\slmult1\sb0\sa140 Body Text;}
{\s17\sbasedon16\snext17\rtlch\af7 \ltrch List;}
{\s18\sbasedon0\snext18\rtlch\af7\afs24\ai \ltrch\loch\sb120\sa120\noline\fs24\i caption;}
{\s19\sbasedon0\snext19\rtlch\af7 \ltrch\loch\noline Index;}
}{\*\generator LibreOffice/25.2.7.2$Windows_X86_64 LibreOffice_project/5cbfd1ab6520636bb5f7b99185aa69bd7456825d}{\info{\creatim\yr2026\mo4\dy30\hr22\min12}{\revtim\yr2026\mo4\dy30\hr22\min13}{\printim\yr0\mo0\dy0\hr0\min0}}{\*\userprops}\deftab709
\hyphauto1\viewscale80\formshade\nobrkwrptbl\paperh15840\paperw12240\margl1134\margr1134\margt1134\margb1134\sectd\sbknone\sftnnar\saftnnrlc\sectunlocked1\pgwsxn12240\pghsxn15840\marglsxn1134\margrsxn1134\margtsxn1134\margbsxn1134\ftnbj\ftnstart1\ftnrstcont\ftnnar\fet\aftnrstcont\aftnstart1\aftnnrlc
{\*\ftnsep\chftnsep}\pgndec\pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Failure Taxonomy Specification v1}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## Purpose}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
This document defines the canonical diagnostic language for runtime scenario observation.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
It exists to standardize failure identification during manual testing.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
This document governs:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- issue classification}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- observational consistency}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- architecture pressure detection}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- roadmap prioritization}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
It does not prescribe solutions.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
It defines problems.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## Core Principle}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Symptoms are not failures.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Failures are underlying system-layer breakdowns.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Example:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Symptom:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Character repeats themselves.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Possible failures:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- retrieval omission}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- memory weighting failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- conflict-state failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- active-window failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
The purpose of this taxonomy is to distinguish them.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Failure Classes}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class A \u8212\'97 Retrieval Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## A1 \u8212\'97 Retrieval Omission Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Relevant memory existed but was not retrieved.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- character forgets important history}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- known conflict ignored}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- known relationship state absent}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- did the memory exist?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- should it have been selected?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## A2 \u8212\'97 Retrieval Irrelevance Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Retrieved memory was not useful to the active scene.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- unrelated facts injected}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- irrelevant history surfaced}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- scene momentum disrupted}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- why was this retrieved?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was scoring poor?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## A3 \u8212\'97 Retrieval Weighting Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Correct memory was retrieved but improperly prioritized.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- low-priority memory dominates behavior}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- high-priority memory underused}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was ranking wrong?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was weighting wrong?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class B \u8212\'97 Continuity Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## B1 \u8212\'97 Continuity Grounding Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Canonical continuity existed but did not influence runtime behavior.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- contradictions}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- forgotten established truths}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- broken scene commitments}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- did continuity exist?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was continuity authoritative?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## B2 \u8212\'97 Continuity Capture Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
A meaningful event occurred but was not captured into continuity.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- future scenes lack important consequences}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- relationship changes vanish}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was extraction incomplete?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was event interpretation weak?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class C \u8212\'97 Identity Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## C1 \u8212\'97 Identity Persistence Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Character loses internal consistency.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- inconsistent motivation}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- sudden emotional discontinuity}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- broken voice}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- did stable identity survive runtime?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## C2 \u8212\'97 Motivation Drift Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Character goal-state becomes unstable or incoherent.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- unexplained priority shifts}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- abandoned active goals}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was goal memory surfaced?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class D \u8212\'97 Relationship Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## D1 \u8212\'97 Relationship Memory Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Relationship history failed to affect behavior.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- trust history ignored}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- betrayal history ignored}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- intimacy history ignored}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was relationship state retrieved?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## D2 \u8212\'97 Relationship Delta Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
New relationship changes were not registered.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- scene interaction changes nothing}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- emotional movement disappears}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was delta extracted?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class E \u8212\'97 Conflict Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## E1 \u8212\'97 Conflict-State Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Active unresolved conflict failed to influence behavior.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- unresolved issues vanish}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- tension collapses}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was conflict memory retrieved?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## E2 \u8212\'97 Escalation Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Conflict exists but fails to evolve.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- repetitive loops}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- static tension}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- no progression}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was progression pressure maintained?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class F \u8212\'97 Memory Structure Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## F1 \u8212\'97 Active Window Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Recent context handling was insufficient.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- immediate context forgotten}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- short-range contradictions}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was local fidelity too weak?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## F2 \u8212\'97 Compression Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Compressed event memory lost critical detail.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- meaningful detail disappeared}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- consequences became distorted}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- was compression too aggressive?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Class G \u8212\'97 Narrative Flow Failures}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## G1 \u8212\'97 Repetition Loop Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Character or scene enters repetition.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- repeated phrases}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- repeated emotional loops}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- repeated behaviors}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- missing new input?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- stuck conflict?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## G2 \u8212\'97 Progression Stall Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Definition:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Scene momentum stops advancing.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Indicators:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- no meaningful change}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- circular dialogue}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- static emotional state}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Questions:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
- missing progression pressure?}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Severity Levels}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## S1 \u8212\'97 Cosmetic}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Minor quality degradation.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
No architectural impact.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## S2 \u8212\'97 Functional}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Behavioral degradation.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Runtime quality impacted.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## S3 \u8212\'97 Structural}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Architecture seam compromised.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Requires issue creation.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
## S4 \u8212\'97 Critical}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Canonical truth or runtime stability compromised.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Immediate issue required.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Observation Recording Format}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Use:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Failure Class:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Severity:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Observed Symptom:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Likely Layer:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Reproducible:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Notes:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Example:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Failure Class: A1 \u8212\'97 Retrieval Omission Failure}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Severity: S2}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Observed Symptom: Character ignored prior betrayal}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Likely Layer: Retrieval Selection}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Reproducible: Yes}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Notes: Betrayal existed in continuity}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
# Rules for Use}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 1:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Classify before fixing.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 2:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Do not use symptom labels as issue labels.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Use taxonomy classes.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 3:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Multiple failure classes may apply.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Choose primary and secondary.}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
---}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Rule 4:}
\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar\loch

\par \pard\plain \s0\rtlch\af6\afs24\alang1081 \ltrch\lang1033\langfe2052\hich\af3\loch\widctlpar\hyphpar0\ltrpar\cf0\f3\fs24\lang1033\kerning1\dbch\af8\langfe2052\ql\ltrpar{\loch
Repeated patterns should influence roadmap priority.}
\par }