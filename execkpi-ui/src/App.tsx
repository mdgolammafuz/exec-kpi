import { useEffect, useState } from "react";
import
  {
    runSQL,
    getABSample,
    runABTest,
    trainML,
    latestML,
  } from "./api";
import type {
  KPIResponse,
  ABSampleResponse,
  ABTestResult,
} from "./api";

type Tab = "kpi" | "ab" | "ml";

const KPI_SQL_FILES = [
  "api_revenue_daily.sql",
  "api_funnel_users.sql",
  "api_ab_group.sql",
  "api_ab_metrics.sql",
  "api_retention_weekly.sql",
  "api_features_conversion.sql",
];

type TabState = {
  output: unknown;
  error: string | null;
};

type ABStatus = { status: "running-ab-test"; alpha: number };

function App ()
{
  const [ tab, setTab ] = useState<Tab>( "kpi" );

  // separate buckets for each tab
  const [ tabData, setTabData ] = useState<Record<Tab, TabState>>( {
    kpi: { output: null, error: null },
    ab: { output: null, error: null },
    ml: { output: null, error: null },
  } );

  const setTabOutput = ( which: Tab, output: unknown ) =>
  {
    setTabData( ( prev ) => ( {
      ...prev,
      [ which ]: { ...prev[ which ], output, error: null },
    } ) );
  };

  const setTabError = ( which: Tab, error: string | null ) =>
  {
    setTabData( ( prev ) => ( {
      ...prev,
      [ which ]: { ...prev[ which ], error },
    } ) );
  };

  const current = tabData[ tab ];

  return (
    <div style={ { maxWidth: 1100, margin: "0 auto", padding: "1.5rem" } }>
      <h1>ExecKPI — Data Gov UI</h1>
      <p style={ { color: "#555" } }>React → FastAPI → BigQuery → dbt → ML.</p>

      <div style={ { display: "flex", gap: "0.5rem", marginBottom: "1rem" } }>
        <button onClick={ () => setTab( "kpi" ) } disabled={ tab === "kpi" }>
          KPI
        </button>
        <button onClick={ () => setTab( "ab" ) } disabled={ tab === "ab" }>
          A/B
        </button>
        <button onClick={ () => setTab( "ml" ) } disabled={ tab === "ml" }>
          ML
        </button>
      </div>

      { tab === "kpi" && (
        <KPIPanel
          setOutput={ ( d ) => setTabOutput( "kpi", d ) }
          setError={ ( e ) => setTabError( "kpi", e ) }
        />
      ) }
      { tab === "ab" && (
        <ABPanel
          setOutput={ ( d ) => setTabOutput( "ab", d ) }
          setError={ ( e ) => setTabError( "ab", e ) }
        />
      ) }
      { tab === "ml" && (
        <MLPanel
          setOutput={ ( d ) => setTabOutput( "ml", d ) }
          setError={ ( e ) => setTabError( "ml", e ) }
        />
      ) }

      <h2 style={ { marginTop: "1.5rem" } }>Result</h2>
      { current.error ? (
        <pre
          style={ {
            background: "#ffefef",
            padding: "1rem",
            border: "1px solid #e99",
          } }
        >
          { current.error }
        </pre>
      ) : (
        <pre
          style={ {
            background: "#111",
            color: "#0f0",
            padding: "1rem",
            minHeight: "150px",
            overflow: "auto",
          } }
        >
          { current.output
            ? JSON.stringify( current.output, null, 2 )
            : "No output yet." }
        </pre>
      ) }
    </div>
  );
}

function KPIPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: KPIResponse | { status: string } ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ start, setStart ] = useState<string>( () =>
    new Date( Date.now() - 30 * 86400000 ).toISOString().slice( 0, 10 )
  );
  const [ end, setEnd ] = useState<string>( () =>
    new Date().toISOString().slice( 0, 10 )
  );
  const [ sqlFile, setSqlFile ] = useState<string>( "api_revenue_daily.sql" );
  const [ loading, setLoading ] = useState( false );

  const fetchKPI = () =>
  {
    setLoading( true );
    setError( null );
    setOutput( { status: "loading-kpi" } );
    runSQL( sqlFile, [
      { name: "start", type: "DATE", value: start },
      { name: "end", type: "DATE", value: end },
    ] )
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" )
      )
      .finally( () => setLoading( false ) );
  };

  return (
    <div>
      <h2>KPI</h2>
      <div style={ { display: "flex", gap: "0.5rem", marginBottom: "0.5rem" } }>
        <label>
          SQL:
          <select
            value={ sqlFile }
            onChange={ ( e ) => setSqlFile( e.target.value ) }
            style={ { marginLeft: "0.25rem" } }
          >
            { KPI_SQL_FILES.map( ( f ) => (
              <option key={ f } value={ f }>
                { f }
              </option>
            ) ) }
          </select>
        </label>
        <label>
          Start:
          <input
            type="date"
            value={ start }
            onChange={ ( e ) => setStart( e.target.value ) }
          />
        </label>
        <label>
          End:
          <input
            type="date"
            value={ end }
            onChange={ ( e ) => setEnd( e.target.value ) }
          />
        </label>
        <button onClick={ fetchKPI } disabled={ loading }>
          { loading ? "Loading…" : "Run" }
        </button>
      </div>
    </div>
  );
}

function ABPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: ABSampleResponse | ABTestResult | ABStatus ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ sample, setSample ] = useState<ABSampleResponse[ "sample" ] | null>( null );
  const [ alpha, setAlpha ] = useState<number>( 0.05 );
  const [ loading, setLoading ] = useState<boolean>( true );
  const [ testing, setTesting ] = useState<boolean>( false );
  const [ panelError, setPanelError ] = useState<string | null>( null );

  // load once on mount
  useEffect( () =>
  {
    const fetchSample = async () =>
    {
      setLoading( true );
      setPanelError( null );
      try
      {
        const data = await getABSample();
        setSample( data.sample );
        setOutput( data );
      } catch ( err )
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
      } finally
      {
        setLoading( false );
      }
    };
    void fetchSample();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [] ); // <- important: don't depend on setOutput, or it'll refetch every render

  const runTest = () =>
  {
    if ( !sample?.A || !sample?.B )
    {
      setPanelError( "Sample not loaded yet. Please retry." );
      return;
    }
    setPanelError( null );
    setError( null );
    setTesting( true );

    // show in result area that we’re running a new test
    setOutput( { status: "running-ab-test", alpha } );

    runABTest( {
      a_success: sample.A.success,
      a_total: sample.A.total,
      b_success: sample.B.success,
      b_total: sample.B.total,
      alpha,
    } )
      .then( ( data ) =>
      {
        setOutput( data );
      } )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setTesting( false ) );
  };

  const retryFetch = () =>
  {
    setLoading( true );
    setPanelError( null );
    getABSample()
      .then( ( data ) =>
      {
        setSample( data.sample );
        setOutput( data );
      } )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
      } )
      .finally( () => setLoading( false ) );
  };

  return (
    <div>
      <h2>A/B</h2>
      { loading ? (
        <p style={ { color: "#777" } }>Loading A/B sample…</p>
      ) : panelError ? (
        <div>
          <p style={ { color: "crimson" } }>Couldn’t load sample.</p>
          <button onClick={ retryFetch }>Retry</button>
        </div>
      ) : sample ? (
        <>
          <p>
            A: { sample.A.success }/{ sample.A.total } | B: { sample.B.success }/
            { sample.B.total }
          </p>
          <label>
            alpha:
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="0.2"
              value={ alpha }
              onChange={ ( e ) => setAlpha( parseFloat( e.target.value ) ) }
            />
          </label>
          <button
            onClick={ runTest }
            style={ { marginLeft: "0.5rem" } }
            disabled={ testing }
          >
            { testing ? "Running…" : "Run test" }
          </button>
          { testing ? (
            <p style={ { color: "#777", marginTop: "0.25rem" } }>
              Testing with α = { alpha } …
            </p>
          ) : null }
        </>
      ) : (
        <p style={ { color: "#777" } }>No sample returned.</p>
      ) }
    </div>
  );
}

function MLPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: unknown ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ training, setTraining ] = useState( false );
  const [ loadingLatest, setLoadingLatest ] = useState( false );
  const [ panelError, setPanelError ] = useState<string | null>( null );

  const handleTrain = () =>
  {
    setTraining( true );
    setPanelError( null );
    setError( null );
    trainML()
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setTraining( false ) );
  };

  const handleLatest = () =>
  {
    setLoadingLatest( true );
    setPanelError( null );
    setError( null );
    latestML()
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setLoadingLatest( false ) );
  };

  return (
    <div>
      <h2>ML</h2>
      <button onClick={ handleTrain } disabled={ training }>
        { training ? "Training…" : "Train (BQ → xgboost)" }
      </button>
      <button
        onClick={ handleLatest }
        style={ { marginLeft: "0.5rem" } }
        disabled={ loadingLatest }
      >
        { loadingLatest ? "Loading latest…" : "Latest" }
      </button>
      { panelError ? (
        <p style={ { color: "crimson" } }>{ panelError }</p>
      ) : (
        <p style={ { color: "#777" } }>
          Uses artifacts/metrics.json from backend.
        </p>
      ) }
    </div>
  );
}

export default App;
